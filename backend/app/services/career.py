"""Career path + skill roadmap: role ladder, the skills the role needs (curated core skills + what current
postings ask for), the user's gaps, and a phased learning plan with free resources and a project per skill."""
import re
from collections import Counter

from app.domain import CareerPath, Resource, RoadmapStep, SearchParams
from app.errors import AllSourcesFailedError
from app.services.career_data import CORE_ENGINEERING, FAMILIES, NPTEL, PROJECTS, RESOURCES, WEEKS
from app.services.search_service import run_search
from app.services.skills import extract_skills

PHASE_WEEKS = 6
MIN_JOBS = 5


def family_for(role: str) -> str | None:
    r = role.lower()
    for key, fam in FAMILIES.items():
        if re.search(fam["match"], r):
            return key
    return None


def _resources(skill: str) -> list[Resource]:
    if skill in RESOURCES:
        return [Resource(title=t, url=u) for t, u in RESOURCES[skill]]
    if skill in CORE_ENGINEERING:
        return [Resource(title=NPTEL[0].format(skill=skill), url=NPTEL[1])]
    return []


def market_demand(role: str, search=None) -> tuple[dict[str, float], int]:
    """Share of current postings for the role that mention each skill."""
    search = search or run_search
    try:
        jobs = search(SearchParams(keywords=role)).jobs[:60]
    except AllSourcesFailedError:
        return {}, 0
    if len(jobs) < MIN_JOBS:
        return {}, len(jobs)
    counts = Counter(s for j in jobs for s in set(extract_skills(f"{j.title}\n{j.description}", with_implied=False)))
    return {s: round(c / len(jobs), 2) for s, c in counts.items()}, len(jobs)


def build_path(role: str, resume_skills: list[str] | None, progress: dict[str, str] | None = None,
               search=None) -> CareerPath:
    fam_key = family_for(role)
    fam = FAMILIES.get(fam_key or "", {})
    path = CareerPath(role=role, family=fam_key,
                      ladder=[{"title": t, "years": y} for t, y in fam.get("ladder", [])],
                      adjacent_roles=fam.get("adjacent", []))
    demand, n = market_demand(role, search)
    path.jobs_sampled = n

    core = fam.get("core", [])
    # required = curated core + skills >= 20% of postings ask for; ranked by market demand, then curated order
    in_demand = [s for s, share in sorted(demand.items(), key=lambda x: -x[1]) if share >= 0.2]
    required = list(dict.fromkeys(core + in_demand))
    required.sort(key=lambda s: (-demand.get(s, 0), core.index(s) if s in core else 99))
    have = set(resume_skills or [])
    progress = progress or {}
    path.have = [s for s in required if s in have]

    gaps = [s for s in required if s not in have and progress.get(s) != "done"] if required else []
    done = [s for s in required if s not in have and progress.get(s) == "done"]
    steps = [RoadmapStep(skill=s, demand_share=demand.get(s), weeks=WEEKS.get(s, 3), status=progress.get(s, "todo"),
                         resources=_resources(s), project=PROJECTS.get(s)) for s in gaps]
    phase, used = [], 0
    for st in steps:  # pack skills into ~6-week phases, in priority order
        if phase and used + st.weeks > PHASE_WEEKS:
            path.phases.append(phase)
            phase, used = [], 0
        phase.append(st)
        used += st.weeks
    if phase:
        path.phases.append(phase)

    if not fam_key:
        path.notes.append(f"No curated career ladder for '{role}' yet; the plan is based on what current postings "
                          "ask for.")
    if not demand:
        path.notes.append("Live postings were unavailable or too few, so the skill list uses the curated core "
                          "skills only."
                          if fam_key else "Not enough data to build a plan: try a more common role name.")
    else:
        path.notes.append(f"Skill demand measured on {n} current postings (often snippets, so rarer skills are "
                          "under-counted).")
    if done:
        path.notes.append(f"Marked done: {', '.join(done)}. Add them to your resume with the project that proves them.")
    if resume_skills is None:
        path.notes.append("Upload your resume so the plan skips skills you already have.")
    return path


def career_reply(p: CareerPath) -> str:
    lines = [f"Career path for {p.role}:"]
    if p.ladder:
        lines.append(" → ".join(f"{s['title']} ({s['years']} yrs)" for s in p.ladder))
    if p.have:
        lines.append(f"You already show: {', '.join(p.have)}.")
    for i, phase in enumerate(p.phases[:3], 1):
        lines.append(f"Phase {i} (~{sum(s.weeks for s in phase)} weeks): " + ", ".join(
            f"{s.skill}" + (f" ({round(s.demand_share * 100)}% of postings)" if s.demand_share else "") for s in phase))
    if not p.phases and p.have:
        lines.append("No gaps in the core skills for this role: focus on projects and interview practice.")
    if p.adjacent_roles:
        lines.append(f"Adjacent roles you could move into: {', '.join(p.adjacent_roles)}.")
    lines += p.notes
    lines.append("Open the Career page to see resources and a project for each skill, and track your progress.")
    return "\n".join(lines)
