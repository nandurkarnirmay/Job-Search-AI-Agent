"""Interview prep: pick questions for a role/job, and give rule-based feedback on typed answers.
The 1-5 score comes from rules so it's reproducible and explainable; the LLM may only add a coaching comment."""
import hashlib
import logging
import re

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.llm import get_llm
from app.domain import AnswerFeedback, FeedbackItem, InterviewQuestion, InterviewReport, SpeechMetrics
from app.models import InterviewSession, User
from app.monitoring import LLM_CALLS
from app.schemas import InterviewOut
from app.services.interview_bank import ALIASES, BEHAVIOURAL, HR, TECHNICAL
from app.services.skills import extract_skills

log = logging.getLogger("app.interview")
MAX_TECHNICAL = 5
MAX_SESSIONS = 30


def _seed(*parts: str) -> int:
    return int(hashlib.sha1("|".join(parts).lower().encode()).hexdigest()[:8], 16)


def _bank_skills(text: str) -> list[str]:
    out = []
    for s in extract_skills(text):
        key = s if s in TECHNICAL else ALIASES.get(s)
        if key and key not in out:
            out.append(key)
    return out


class _Generated(BaseModel):
    questions: list[str]


GEN_PROMPT = """Write {n} interview questions a hiring manager in India would ask a candidate for the role "{role}"{at}.
Focus on practical, role-specific technical judgement. One sentence each, ending with a question mark.
Don't repeat these: {existing}"""


def build_questions(role: str, company: str | None = None,
                    description: str = "") -> tuple[list[InterviewQuestion], list[str]]:
    """(questions, notes). Deterministic for the same inputs, so a session can be regenerated identically."""
    notes: list[str] = []
    seed = _seed(role, company or "", description[:200])
    qs: list[InterviewQuestion] = []

    def add(q: dict, category: str, skill: str | None = None, source: str = "bank"):
        text = q["text"].format(company=company or "our company", role=role)
        qs.append(InterviewQuestion(id=f"q{len(qs) + 1}", text=text, category=category, skill=skill,
                                    key_points=q.get("key_points", []), source=source))

    add(HR[0], "hr")  # tell me about yourself: always first
    add(HR[1] if company else HR[2], "hr")

    skills = _bank_skills(f"{role}\n{description}")
    if not skills:
        notes.append(f"No technical question bank matches '{role}' yet, so the technical round is short.")
    # round-robin over the role's skills: each skill's first question, then second ones, max MAX_TECHNICAL.
    # Starting index depends on the seed, so different roles get different questions from the same bank.
    picked = 0
    for round_ in range(2):
        for s in skills:
            bank = TECHNICAL[s]
            if round_ < len(bank) and picked < MAX_TECHNICAL:
                add(bank[(seed + round_) % len(bank)], "technical", s)
                picked += 1

    for i in range(2):
        add(BEHAVIOURAL[(seed + i * 3) % len(BEHAVIOURAL)], "behavioural")
    add(HR[3 + seed % 3], "hr")  # notice period / salary in LPA / relocation: India-specific

    llm = get_llm()
    if llm is not None:
        try:
            gen = llm.with_structured_output(_Generated).invoke(GEN_PROMPT.format(
                n=2, role=role, at=f" at {company}" if company else "", existing="; ".join(q.text for q in qs)))
            LLM_CALLS.labels("interview_questions", "ok").inc()
            for text in gen.questions[:2]:
                text = text.strip()
                if 15 < len(text) < 250 and text.endswith("?") and text not in {q.text for q in qs}:
                    add({"text": text}, "technical", None, "llm")
        except Exception as e:
            LLM_CALLS.labels("interview_questions", "error").inc()
            log.warning("question generation failed: %s", e)
    for i, q in enumerate(qs, 1):
        q.id = f"q{i}"
    return qs, notes


# ---------------- answer feedback ----------------

_WORDS = re.compile(r"[A-Za-z0-9']+")
_SITUATION = re.compile(r"\b(when|during|while|at (?:my|our|an?|the)|in my|project|internship|semester|team|client|"
                        r"company|college|hackathon|course)\b", re.I)
_ACTION = re.compile(r"\bI (?:\w+ly )?(?:built|led|wrote|designed|created|implemented|analy[sz]ed|organi[sz]ed|fixed|"
                     r"proposed|decided|automated|learned|learnt|reached|spoke|talked|negotiated|took|set up|developed|"
                     r"managed|coordinated|tested|debugged|reviewed|planned|researched|split|prioriti[sz]ed|asked|"
                     r"started|changed|introduced|used|trained|deployed|presented)\b", re.I)
_RESULT = re.compile(r"\b(result|outcome|as a result|so that|which (?:led|helped)|led to|improv\w*|reduc\w*|"
                     r"increas\w*|sav\w*|achiev\w*|won|delivered|completed|launched|on time|feedback|learned|learnt)\b",
                     re.I)
_METRIC = re.compile(r"\d+(?:\.\d+)?\s*(?:%|percent|x\b|hours?|hrs?|days?|weeks?|months?|users?|customers?|rows|"
                     r"lakh|lakhs|crore|lpa|rs\.?|₹|inr|ms|seconds?|minutes?)|\b\d{2,}\b", re.I)
_FILLER = re.compile(r"\b(basically|actually|literally|you know|kind of|sort of|like,)\b", re.I)


def _length_item(n: int, lo: int, hi: int) -> FeedbackItem:
    if n < lo // 2:
        return FeedbackItem(name="Length", score=0.2, comment=f"{n} words is far too short; aim for {lo}–{hi}.")
    if n < lo:
        return FeedbackItem(name="Length", score=0.6, comment=f"{n} words: a bit short; aim for {lo}–{hi}.")
    if n > hi * 1.5:
        return FeedbackItem(name="Length", score=0.4, comment=f"{n} words: too long to say in ~2 minutes; cut to {hi}.")
    return FeedbackItem(name="Length", score=1.0, comment=f"{n} words: good length.")


def _hr_specific(q: InterviewQuestion, a: str, company: str | None) -> list[FeedbackItem]:
    t = q.text.lower()
    items = []
    if "notice period" in t:
        ok = bool(re.search(r"\d+\s*days?|immediate|\d+\s*months?|serving", a, re.I))
        items.append(FeedbackItem(name="Clear answer", score=1.0 if ok else 0.3,
                                  comment="States the notice period clearly." if ok else
                                  "Say the exact number of days (e.g. '60 days, negotiable to 30') or 'immediate'."))
    elif "salary" in t:
        num = bool(re.search(r"\d+(?:\.\d+)?\s*(?:-|to|–)?\s*\d*\s*(?:lpa|lakhs?|l\b|lacs?)", a, re.I))
        why = bool(re.search(r"based on|research|market|glassdoor|ambitionbox|naukri|current|experience|role", a, re.I))
        items.append(FeedbackItem(name="Concrete range", score=1.0 if num else 0.3,
                                  comment="Gives a number in LPA." if num else
                                  "Give a range in LPA, not 'as per company norms'."))
        items.append(FeedbackItem(name="Justified", score=1.0 if why else 0.4,
                                  comment="Explains the basis." if why else
                                  "Say what the range is based on (market data, role, skills)."))
    elif "join" in t and company:
        specific = company.lower().split()[0] in a.lower() or bool(re.search(
            r"product|mission|customers?|values|culture|growth|technology|team|domain|clients?", a, re.I))
        items.append(FeedbackItem(name="Company-specific", score=1.0 if specific else 0.3,
                                  comment="Connects to the company." if specific else
                                  f"Mention something specific about {company}: a product, customer or initiative."))
    elif "about yourself" in t:
        parts = sum(bool(re.search(p, a, re.I)) for p in (
            r"b\.?tech|degree|student|graduat|engineer|currently|final[- ]year",
            r"intern|project|worked|built|experience", r"looking|goal|want to|excited|aim|next|role"))
        items.append(FeedbackItem(name="Present–past–future", score=parts / 3,
                                  comment="Covers who you are, what you've done and what you want." if parts == 3 else
                                  "Structure it: who you are now → what you've done (1–2 highlights) → why this role."))
    return items


def evaluate_answer(q: InterviewQuestion, answer: str, company: str | None = None) -> AnswerFeedback:
    words = len(_WORDS.findall(answer))
    items: list[FeedbackItem] = []
    hit, missed, tips = [], [], []

    if q.category == "technical" and q.key_points:
        for label, pattern in q.key_points:
            (hit if re.search(pattern, answer, re.I) else missed).append(label)
        cov = len(hit) / len(q.key_points)
        items.append(FeedbackItem(name="Key points", score=cov,
                                  comment=f"Covered {len(hit)} of {len(q.key_points)} key points."))
        items.append(_length_item(words, 40, 180))
        if missed:
            tips.append(f"Also cover: {', '.join(missed)}.")
        if not re.search(r"example|for instance|e\.g\.|such as|in my project|i used", answer, re.I):
            tips.append("Add a short example from your own work: it shows you've used it, not just read about it.")
    elif q.category == "technical":  # LLM-generated: no key points, judge structure
        items.append(_length_item(words, 40, 180))
        has_example = bool(re.search(r"example|for instance|in my|i used|i built", answer, re.I))
        items.append(FeedbackItem(name="Concrete example", score=1.0 if has_example else 0.4,
                                  comment="Uses a real example." if has_example else "Back it with an example."))
    else:
        if q.category == "behavioural":
            star = {"Situation": _SITUATION, "Action (what *you* did)": _ACTION, "Result": _RESULT}
            for name, pat in star.items():
                ok = bool(pat.search(answer))
                items.append(FeedbackItem(name=name, score=1.0 if ok else 0.0,
                                          comment="Present." if ok else
                                          f"Missing: add the {name.split(' ')[0].lower()}."))
            metric = bool(_METRIC.search(answer))
            items.append(FeedbackItem(name="Measurable impact", score=1.0 if metric else 0.3,
                                      comment="Quantifies the outcome." if metric else
                                      "Quantify the result (%, time saved, users, ₹)."))
            n_i = len(re.findall(r"\bI\b", answer))
            n_we = len(re.findall(r"\bwe\b", answer, re.I))
            if n_we >= 3 and n_we > 2 * n_i:
                tips.append("You say 'we' much more than 'I': make your own contribution explicit.")
        items += _hr_specific(q, answer, company)
        factual = re.search(r"notice period|salary|relocat", q.text, re.I)  # good answers are 1-3 sentences
        items.append(_length_item(words, 15, 90) if factual else _length_item(words, 60, 220))

    fillers = len(_FILLER.findall(answer))
    if fillers >= 3:
        tips.append(f"{fillers} filler words ('basically', 'actually'…): they weaken spoken answers.")
    avg = sum(i.score for i in items) / len(items)
    score = 1 + round(4 * avg)
    if words < 8:
        score = 1
    tips += [i.comment for i in items if i.score < 0.7 and i.comment not in tips][:3]

    fb = AnswerFeedback(score=score, word_count=words, criteria=items, key_points_hit=hit,
                        key_points_missed=missed, tips=tips)
    fb.coach_comment = _coach(q, answer, fb)
    return fb


COACH_PROMPT = """You are an interview coach. In 2 sentences, give the candidate the single most useful improvement
for this answer. Don't restate a score, don't praise generically, and don't assume facts about the candidate.
Question: {q}
Answer: {a}"""


def _coach(q: InterviewQuestion, answer: str, fb: AnswerFeedback) -> str | None:
    llm = get_llm()
    if llm is None or fb.word_count < 8:
        return None
    try:
        text = llm.invoke(COACH_PROMPT.format(q=q.text, a=answer[:2000])).content
        LLM_CALLS.labels("interview_coach", "ok").inc()
        text = (text if isinstance(text, str) else str(text)).strip()
        return text[:600] or None
    except Exception as e:
        LLM_CALLS.labels("interview_coach", "error").inc()
        log.warning("coach comment failed: %s", e)
        return None


# ---------------- persistence ----------------

def interview_out(s: InterviewSession, notes: list[str] | None = None) -> InterviewOut:
    return InterviewOut(id=s.id, role=s.role, company=s.company, questions=s.questions, answers=s.answers or {},
                        notes=notes or [], created_at=s.created_at)


def create_session(db: Session, user: User, role: str, company: str | None,
                   description: str = "") -> tuple[InterviewSession, list[str]]:
    questions, notes = build_questions(role, company, description)
    s = InterviewSession(user_id=user.id, role=role[:120], company=(company or None) and company[:200],
                         questions=[q.model_dump() for q in questions], answers={})
    db.add(s)
    db.commit()
    old = db.scalars(select(InterviewSession).where(InterviewSession.user_id == user.id)
                     .order_by(InterviewSession.id.desc()).offset(MAX_SESSIONS)).all()
    for o in old:  # keep the latest sessions only
        db.delete(o)
    db.commit()
    return s, notes




# ---------------- Week 6: spoken answers, follow-ups, session report ----------------
SPOKEN_FILLERS = re.compile(r"\b(um+|uh+|erm|hmm|basically|actually|literally|you know|kind of|sort of|like|so yeah)\b",
                            re.I)
PACE = (110, 160)  # comfortable interview pace, words per minute


def speech_items(answer: str, duration_seconds: float, long_pauses: int) -> tuple[SpeechMetrics, list[FeedbackItem]]:
    words = max(len(_WORDS.findall(answer)), 1)
    wpm = round(words / max(duration_seconds, 1) * 60)
    fillers = round(len(SPOKEN_FILLERS.findall(answer)) / words * 100, 1)
    m = SpeechMetrics(duration_seconds=round(duration_seconds, 1), words_per_minute=wpm,
                      filler_per_100_words=fillers, long_pauses=long_pauses)
    lo, hi = PACE
    pace = FeedbackItem(name="Pace", score=1.0 if lo <= wpm <= hi else 0.5 if lo - 30 <= wpm <= hi + 30 else 0.2,
                        comment=f"{wpm} words/min: " + ("comfortable." if lo <= wpm <= hi else
                                                         "a bit slow; tighten it." if wpm < lo else
                                                         "too fast; slow down and pause between points."))
    smooth = fillers <= 3 and long_pauses <= 2
    fluency = FeedbackItem(name="Fluency", score=1.0 if smooth else 0.5 if fillers <= 7 else 0.2,
                           comment=f"{fillers} filler words per 100 words, {long_pauses} long pauses. "
                                   + ("Smooth delivery." if smooth else
                                      "Replace fillers with a short silent pause."))
    return m, [pace, fluency]


def evaluate_spoken(q: InterviewQuestion, answer: str, duration_seconds: float, long_pauses: int,
                    company: str | None = None) -> AnswerFeedback:
    """Content checks as for typed answers, plus delivery (pace, fillers, pauses), folded into the 1-5 score."""
    fb = evaluate_answer(q, answer, company)
    metrics, items = speech_items(answer, duration_seconds, long_pauses)
    fb.speech, fb.criteria = metrics, fb.criteria + items
    if fb.word_count >= 8:
        fb.score = 1 + round(4 * sum(c.score for c in fb.criteria) / len(fb.criteria))
    fb.tips += [i.comment for i in items if i.score < 0.7]
    return fb


FOLLOWUP_PROMPT = """You are interviewing a candidate for {role}. Ask ONE short follow-up question that probes the
weakest part of their answer (a missing detail, a claim without evidence, or their own contribution).
Question: {q}
Answer: {a}
Reply with the question only."""


def followup_for(q: InterviewQuestion, answer: str, fb: AnswerFeedback, role: str, existing_ids: set[str]) \
        -> InterviewQuestion | None:
    """One follow-up per original question (never for follow-ups), like a real interviewer digging in."""
    if q.source == "followup" or f"{q.id}f" in existing_ids or fb.word_count < 8:
        return None
    text = None
    llm = get_llm()
    if llm is not None:
        try:
            out = llm.invoke(FOLLOWUP_PROMPT.format(role=role, q=q.text, a=answer[:1500])).content
            out = (out if isinstance(out, str) else str(out)).strip().strip('"')
            LLM_CALLS.labels("interview_followup", "ok").inc()
            if 10 < len(out) < 250 and out.endswith("?"):
                text = out
        except Exception as e:
            LLM_CALLS.labels("interview_followup", "error").inc()
            log.warning("follow-up generation failed: %s", e)
    if text is None:  # rule-based follow-ups from what the feedback found missing
        names = {c.name: c.score for c in fb.criteria}
        if fb.key_points_missed:
            text = f"You didn't mention {fb.key_points_missed[0]}. Can you explain that part?"
        elif names.get("Action (what *you* did)", 1) < 1:
            text = "What exactly did you do yourself, as opposed to the team?"
        elif names.get("Result", 1) < 1 or names.get("Measurable impact", 1) < 1:
            text = "What was the measurable outcome, and how did you know it worked?"
        elif names.get("Justified", 1) < 1:
            text = "How did you arrive at that number?"
        elif q.category == "technical":
            text = "Can you give an example of where you used this in a project, and what went wrong?"
        else:
            return None
    return InterviewQuestion(id=f"{q.id}f", text=text, category=q.category, skill=q.skill, source="followup",
                             parent_id=q.id)


def session_report(questions: list[dict], answers: dict) -> InterviewReport:
    qs = {q["id"]: q for q in questions}
    scored = [(qs[qid], a["feedback"]) for qid, a in answers.items() if qid in qs and a.get("feedback")]
    rep = InterviewReport(answered=len(scored), total=len(questions))
    if not scored:
        rep.next_steps.append("Answer at least a few questions to get a report.")
        return rep
    scores = [fb["score"] for _, fb in scored]
    rep.average_score = round(sum(scores) / len(scores), 1)
    cats: dict[str, list[int]] = {}
    for q, fb in scored:
        cats.setdefault(q["category"], []).append(fb["score"])
    rep.by_category = {c: round(sum(v) / len(v), 1) for c, v in cats.items()}
    ranked = sorted(scored, key=lambda x: x[1]["score"])
    rep.weakest = [{"question": q["text"], "score": fb["score"]} for q, fb in ranked if fb["score"] <= 3][:2]
    rep.strongest = [{"question": q["text"], "score": fb["score"]} for q, fb in ranked[::-1] if fb["score"] >= 4][:2]
    wpms = [fb["speech"]["words_per_minute"] for _, fb in scored if fb.get("speech")]
    rep.average_wpm = round(sum(wpms) / len(wpms)) if wpms else None
    tip_counts: dict[str, int] = {}
    for _, fb in scored:
        for tip in fb.get("tips", []):
            key = re.sub(r"\d+", "#", tip)  # "45 words: a bit short" and "30 words: …" are the same tip
            tip_counts[key] = tip_counts.get(key, 0) + 1
    rep.recurring_tips = [t for t, n in sorted(tip_counts.items(), key=lambda x: -x[1]) if n >= 2][:3]
    weakest_cat = min(rep.by_category, key=rep.by_category.get)
    rep.next_steps.append(f"Your weakest area is {weakest_cat} questions (avg {rep.by_category[weakest_cat]}/5): "
                          "practise 3 more of those before the interview.")
    if rep.answered < rep.total:
        left = rep.total - rep.answered
        rep.next_steps.append(f"{left} question{'s' if left != 1 else ''} still unanswered.")
    if rep.average_wpm and not PACE[0] <= rep.average_wpm <= PACE[1]:
        rep.next_steps.append(f"Your average pace is {rep.average_wpm} words/min; aim for {PACE[0]}–{PACE[1]}.")
    return rep
