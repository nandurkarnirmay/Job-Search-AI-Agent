"""GitHub profile analysis for job seekers: what your public work shows, how it lines up with your resume,
and concrete fixes recruiters notice (descriptions, recent activity, pinned original work)."""
import json
import re
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache

from app.cache import get_cache
from app.domain import FeedbackItem, GitHubReport, RepoSummary
from app.errors import AppError
from app.services.skills import extract_skills
from app.sources.base import SourceError
from app.sources.github import GitHubClient

USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")
CACHE_TTL = 86400
# GitHub's language names -> our skills taxonomy
LANGUAGE_SKILLS = {"Python": "Python", "Jupyter Notebook": "Python", "Java": "Java", "JavaScript": "JavaScript",
                   "TypeScript": "TypeScript", "C++": "C++", "C": "C", "C#": "C#", "Go": "Go", "Rust": "Rust",
                   "Kotlin": "Kotlin", "Swift": "Swift", "PHP": "PHP", "Ruby": "Ruby", "Scala": "Scala", "R": "R",
                   "MATLAB": "MATLAB", "Shell": "Bash", "HTML": "HTML", "CSS": "CSS", "Dart": "Flutter",
                   "Vue": "Vue", "VBA": "VBA", "Dockerfile": "Docker", "HCL": "Terraform"}


@lru_cache
def get_github_client() -> GitHubClient:
    return GitHubClient()


def _years_since(iso: str | None, now: datetime) -> float:
    if not iso:
        return 0.0
    then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return round((now - then).days / 365.25, 1)


def analyse(username: str, resume_skills: list[str] | None = None, now: datetime | None = None) -> GitHubReport:
    username = username.strip().lstrip("@")
    if not USERNAME.match(username):
        raise AppError("That isn't a valid GitHub username.", code="validation_error", status_code=422)
    now = now or datetime.now(timezone.utc)
    cache = get_cache()
    key = f"github:{username.lower()}"
    if cached := cache.get(key):
        user, repos = json.loads(cached)
    else:
        try:
            client = get_github_client()
            user = client.user(username)
            if user is None:
                raise AppError(f"No GitHub user called '{username}'.", code="not_found", status_code=404)
            repos = client.repos(username)
        except SourceError as e:
            raise AppError("GitHub is unavailable right now (or the hourly limit was reached). Try again later.",
                           code="github_unavailable", status_code=503) from e
        cache.set(key, json.dumps([user, repos]), CACHE_TTL)
    return build_report(user, repos, resume_skills, now)


def build_report(user: dict, repos: list[dict], resume_skills: list[str] | None, now: datetime) -> GitHubReport:
    original = [r for r in repos if not r.get("fork") and not r.get("archived")]
    langs = Counter(r["language"] for r in original if r.get("language"))
    six_months = [r for r in original if r.get("pushed_at") and _years_since(r["pushed_at"], now) <= 0.5]
    text = " ".join(f"{r.get('name', '')} {r.get('description') or ''} {' '.join(r.get('topics') or [])}"
                    for r in original)
    skills = set(extract_skills(text.replace("-", " ")))
    skills |= {LANGUAGE_SKILLS[lang] for lang in langs if lang in LANGUAGE_SKILLS}
    ranked = sorted(original, key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at") or ""), reverse=True)

    rep = GitHubReport(
        username=user["login"], profile_url=user.get("html_url") or f"https://github.com/{user['login']}",
        name=user.get("name"), bio=user.get("bio"), public_repos=user.get("public_repos", 0),
        original_repos=len(original), followers=user.get("followers", 0),
        account_years=_years_since(user.get("created_at"), now), active_repos_6m=len(six_months),
        total_stars=sum(r.get("stargazers_count", 0) for r in original), languages=dict(langs.most_common()),
        skills=sorted(skills),
        top_repos=[RepoSummary(name=r["name"], url=r["html_url"], language=r.get("language"),
                               stars=r.get("stargazers_count", 0), description=r.get("description"),
                               pushed_at=r.get("pushed_at")) for r in ranked[:6]],
    )
    if resume_skills is not None:
        have = set(resume_skills)
        rep.missing_from_resume = sorted(skills - have)
        rep.unproven_on_github = sorted(s for s in have - skills if s in set(LANGUAGE_SKILLS.values())
                                        | {"React", "Django", "Flask", "FastAPI", "Spring Boot", "Node.js",
                                           "Machine Learning", "Deep Learning", "Docker", "SQL", "Pandas"})
    else:
        rep.notes.append("Upload your resume to compare it with your GitHub.")

    described = sum(1 for r in original if (r.get("description") or "").strip())
    rep.checks = [
        FeedbackItem(name="Original projects", score=min(len(original) / 4, 1.0),
                     comment=f"{len(original)} original (non-fork) "
                             f"repositor{'y' if len(original) == 1 else 'ies'}. Recruiters look for 3–6 solid ones."),
        FeedbackItem(name="Recent activity", score=1.0 if six_months else 0.2,
                     comment=f"{len(six_months)} repositories updated in the last 6 months." if six_months else
                     "Nothing pushed in 6 months: a recent project shows you're still building."),
        FeedbackItem(name="Descriptions", score=described / len(original) if original else 0.0,
                     comment=f"{described}/{len(original)} repositories have a description. Add one line saying "
                             "what each project does and the stack."),
        FeedbackItem(name="Profile bio", score=1.0 if user.get("bio") else 0.3,
                     comment="Bio is set." if user.get("bio") else
                     "Add a bio: role you want + 2–3 core skills (e.g. 'Data analyst · Python · SQL · Power BI')."),
    ]
    if not original:
        rep.notes.append("No original public repositories yet: start with one project that matches your target role.")
    rep.notes.append("Only public data is used. Pin your 3–6 best repositories on your profile; GitHub's API "
                     "doesn't expose pins, so they aren't checked here.")
    return rep


def github_reply(r: GitHubReport) -> str:
    def n(k: int, word: str) -> str:
        return f"{k} {word}{'' if k == 1 else 's'}"

    lines = [f"GitHub @{r.username}: {n(r.original_repos, 'original repo')}, {r.active_repos_6m} active in the last "
             f"6 months, {n(r.total_stars, 'star')}."]
    if r.languages:
        lines.append("Languages: " + ", ".join(f"{k} ({v})" for k, v in list(r.languages.items())[:6]))
    if r.missing_from_resume:
        lines.append(f"On GitHub but not on your resume: {', '.join(r.missing_from_resume)}. Add them if the "
                     "projects are substantial.")
    if r.unproven_on_github:
        lines.append(f"On your resume with no public project: {', '.join(r.unproven_on_github)}. A small project "
                     "for each makes the claim credible.")
    weak = [c for c in r.checks if c.score < 0.7]
    if weak:
        lines.append("\nTo improve:")
        lines += [f"• {c.comment}" for c in weak]
    return "\n".join(lines)
