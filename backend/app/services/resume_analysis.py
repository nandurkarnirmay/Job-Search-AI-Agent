"""ATS match against one job, and skill-gap review against the market for a role. Deterministic, no LLM:
the score must be explainable and reproducible (same resume + same job = same score)."""
import re
from collections import Counter

from app.domain import ATSMatch, ParsedResume, ResumeReview, SearchParams, SkillDemand
from app.errors import AllSourcesFailedError
from app.services.search_service import run_search
from app.services.skills import extract_skills, skill_positions

PREFERRED_HINT = re.compile(r"\b(nice to have|good to have|preferred|preferably|a plus|is a plus|plus point|bonus|"
                            r"desirable|added advantage|advantageous|familiarity|exposure to|optional)\b", re.I)
_TITLE_STOP = {"senior", "sr", "junior", "jr", "lead", "trainee", "intern", "internship", "associate", "i", "ii", "iii",
               "iv", "level", "grade", "fresher", "freshers", "graduate", "the", "and", "of", "for", "in", "at", "with",
               "remote", "hybrid", "urgent", "hiring", "immediate", "joiner", "job", "opening", "role", "position"}

WEIGHT_REQUIRED, WEIGHT_PREFERRED = 2, 1
SKILLS_POINTS, TITLE_POINTS = 70, 15
STRUCTURE_POINTS = {"experience": 4, "education": 3, "skills": 4, "projects": 2}  # + contact 2 = 15
CONTACT_POINTS = 2
MIN_JOBS_FOR_DEMAND = 5


_OR = re.compile(r"\s+(?:or|and/or)\s+", re.I)
_HARD_EDGE = re.compile(r"[:;()]|\s+and\s+(?!/)|\s+with\s+", re.I)


def _or_groups(sentence: str) -> list[list[str]]:
    """Alternatives count as one requirement, met by any of them:
    "dashboards in Power BI or Tableau" -> [Power BI, Tableau]; "Java, Scala or Go" -> [Java, Scala, Go]."""
    groups = []
    for m in _OR.finditer(sentence):
        left = _HARD_EDGE.split(sentence[:m.start()])[-1]
        right = re.split(r"[,:;()]|\s+and\s+", sentence[m.end():])[0]
        right_sk = skill_positions(right)[:1]
        segments = left.split(",")
        left_sk = skill_positions(segments[-1])[-1:]          # skill right before "or"
        for seg in reversed(segments[:-1]):                    # walk back through "A, B, C or D"
            seg_sk = skill_positions(seg)
            if not seg_sk:
                break
            left_sk = seg_sk[-1:] + left_sk
        if left_sk and right_sk:
            groups.append(list(dict.fromkeys(left_sk + right_sk)))
    merged: list[list[str]] = []                               # "A or B or C" -> one group
    for g in groups:
        for existing in merged:
            if set(g) & set(existing):
                existing.extend(s for s in g if s not in existing)
                break
        else:
            merged.append(g)
    return merged


def classify_job_skills(description: str) -> tuple[list[list[str]], list[list[str]]]:
    """(required, preferred) as requirement groups; a group is met if the resume has ANY skill in it.
    A skill in a 'nice to have / preferred' sentence is preferred; anywhere else it's required.
    Mentioned as required anywhere wins."""
    required: list[list[str]] = []
    preferred: list[list[str]] = []
    for sentence in re.split(r"[\n.;•\u2022|]+", description):
        skills = extract_skills(sentence, with_implied=False)
        if not skills:
            continue
        target = preferred if PREFERRED_HINT.search(sentence) else required
        groups = _or_groups(sentence)
        grouped = {s for g in groups for s in g}
        for g in groups + [[s] for s in skills if s not in grouped]:
            if not any(set(g) <= set(existing) for existing in target):
                target.append(g)
    req_skills = {s for g in required for s in g}
    preferred = [g for g in preferred if not set(g) & req_skills]
    return required, preferred


def _label(group: list[str]) -> str:
    return " or ".join(group)


def _title_words(title: str) -> list[str]:
    words = re.findall(r"[a-z0-9+#.]+", title.lower())
    return [w.strip(".") for w in words if w.strip(".") and w.strip(".") not in _TITLE_STOP and not w.isdigit()]


def ats_match(resume: ParsedResume, job_title: str, description: str, company: str | None = None) -> ATSMatch:
    have = set(resume.skills)  # includes implied skills (MySQL counts for SQL)
    req, pref = classify_job_skills(f"{job_title}\n{description}")
    m = ATSMatch(score=0, skills_score=0, title_score=0, structure_score=0, job_title=job_title, company=company)

    def met(g: list[str]) -> list[str]:
        return [s for s in g if s in have]

    m.matched_required = [s for g in req for s in met(g)]
    m.missing_required = [_label(g) for g in req if not met(g)]
    m.matched_preferred = [s for g in pref for s in met(g)]
    m.missing_preferred = [_label(g) for g in pref if not met(g)]

    total_w = WEIGHT_REQUIRED * len(req) + WEIGHT_PREFERRED * len(pref)
    got_w = WEIGHT_REQUIRED * sum(1 for g in req if met(g)) + WEIGHT_PREFERRED * sum(1 for g in pref if met(g))

    words = _title_words(job_title)
    text = resume.text.lower()
    hits = [w for w in words if re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", text)]
    m.title_score = round(TITLE_POINTS * (len(hits) / len(words) if words else 0.5), 1)
    m.structure_score = float(sum(p for sec, p in STRUCTURE_POINTS.items() if resume.sections.get(sec))
                              + (CONTACT_POINTS if resume.has_contact else 0))

    if total_w:
        m.skills_score = round(SKILLS_POINTS * got_w / total_w, 1)
        m.score = round(m.skills_score + m.title_score + m.structure_score)
    else:
        # no recognisable skills in the posting: scale title+structure to 100 but say it's low-confidence
        m.score = round((m.title_score + m.structure_score) / (TITLE_POINTS + 15) * 100)
        m.notes.append("Couldn't identify specific skills in this job description, so the score only reflects the "
                       "job title and your resume's structure. Treat it as a rough indicator.")
    if len(description) < 400:
        m.notes.append("Only a short job snippet was available; open the full posting to check every requirement.")

    for s in m.missing_required[:5]:
        m.suggestions.append(f"The job asks for {s}. If you've genuinely used it, show it in a project or internship "
                             f"bullet (what you built with it and the result), not only in the skills list.")
    missing_title = [w for w in words if w not in hits]
    if missing_title:
        m.suggestions.append(f"The title words {', '.join(repr(w) for w in missing_title)} don't appear in your "
                             "resume. If the role fits you, use the same wording in your summary.")
    m.suggestions += [w for w in resume.warnings if "heading" in w or "contact" in w.lower() or "text" in w]
    return m


def review_for_role(resume: ParsedResume, role: str | None, search=None) -> ResumeReview:
    """Structure feedback + which skills the market asks for in this role and whether the resume shows them."""
    search = search or run_search
    rev = ResumeReview(role=role, skills=resume.skills, warnings=resume.warnings, sections=resume.sections)
    if not role:
        rev.notes.append("Tell me a target role (or set one in your profile) to compare your skills with the market.")
        return rev
    try:
        jobs = search(SearchParams(keywords=role)).jobs[:60]
    except AllSourcesFailedError:
        rev.notes.append("Job sources are unavailable right now, so the market comparison is missing.")
        return rev
    rev.jobs_sampled = len(jobs)
    if len(jobs) < MIN_JOBS_FOR_DEMAND:
        rev.notes.append(f"Only {len(jobs)} job(s) found for '{role}': too few to measure skill demand.")
        return rev
    counts = Counter(s for j in jobs for s in set(extract_skills(f"{j.title}\n{j.description}", with_implied=False)))
    have = set(resume.skills)
    rev.demand = [SkillDemand(skill=s, share=round(c / len(jobs), 2), have=s in have)
                  for s, c in counts.most_common(15) if c / len(jobs) >= 0.08][:12]
    rev.notes.append(f"Based on {len(jobs)} current '{role}' postings (job sources often show only a snippet of "
                     "the description, so less common skills are under-counted).")
    return rev


def ats_reply(m: ATSMatch) -> str:
    where = f" at {m.company}" if m.company else ""
    lines = [f"ATS match for {m.job_title}{where}: {m.score}/100",
             f"(skills {m.skills_score:g}/70 · title {m.title_score:g}/15 · structure {m.structure_score:g}/15)"]
    if m.matched_required:
        lines.append(f"✓ You show: {', '.join(m.matched_required + m.matched_preferred)}")
    if m.missing_required:
        lines.append(f"✗ Missing (required): {', '.join(m.missing_required)}")
    if m.missing_preferred:
        lines.append(f"○ Missing (nice to have): {', '.join(m.missing_preferred)}")
    if m.suggestions:
        lines.append("\nTo improve:")
        lines += [f"• {s}" for s in m.suggestions[:5]]
    lines += m.notes
    return "\n".join(lines)


def review_reply(r: ResumeReview) -> str:
    lines = [f"Resume check: {len(r.skills)} skills detected ({', '.join(r.skills[:12])}"
             f"{'…' if len(r.skills) > 12 else ''})." if r.skills else "Resume check: no skills detected."]
    if r.warnings:
        lines.append("Fix first:")
        lines += [f"• {w}" for w in r.warnings]
    if r.demand:
        missing = [d for d in r.demand if not d.have]
        lines.append(f"\nMost-requested skills for {r.role}:")
        lines += [f"{'✓' if d.have else '✗'} {d.skill}: in {round(d.share * 100)}% of postings" for d in r.demand]
        if missing:
            lines.append(f"\nBiggest gaps: {', '.join(d.skill for d in missing[:3])}. Learn and show them through a "
                         "project before claiming them on your resume.")
    lines += r.notes
    return "\n".join(lines)
