"""Week 5 career tools: salary benchmarking, offer negotiation, career path roadmaps, GitHub profile analysis."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, rate_limited
from app.domain import CareerPath, GitHubReport, NegotiationAdvice, SalaryReport, SearchParams
from app.errors import AppError
from app.models import SkillProgress, User
from app.schemas import GitHubIn, NegotiationIn, SkillStatusIn
from app.services.career import build_path
from app.services.github_profile import analyse
from app.services.negotiation import advise
from app.services.salary_research import research_salary

router = APIRouter(tags=["career"])


def resume_skills(user: User) -> list[str] | None:
    return list(user.resume.skills) if user.resume else None


def progress_of(db: Session, user: User) -> dict[str, str]:
    return {p.skill: p.status for p in db.scalars(select(SkillProgress).where(SkillProgress.user_id == user.id))}


@router.get("/salary/benchmark", response_model=SalaryReport)
def benchmark(role: str = Query(min_length=2, max_length=100), city: str | None = Query(default=None, max_length=60),
              experience_years: float | None = Query(default=None, ge=0, le=50), _: User = Depends(rate_limited)):
    return research_salary(SearchParams(keywords=role, city=city, max_experience_years=experience_years))


@router.post("/salary/negotiate", response_model=NegotiationAdvice)
def negotiate(body: NegotiationIn, user: User = Depends(rate_limited)):
    name = user.profile.full_name if user.profile else None
    return advise(body.role, body.offer_lpa, city=body.city, experience_years=body.experience_years,
                  current_lpa=body.current_lpa, competing_lpa=body.competing_offer_lpa,
                  notice_period_days=body.notice_period_days, skills=resume_skills(user), name=name)


@router.get("/career/path", response_model=CareerPath)
def career_path(role: str | None = Query(default=None, min_length=2, max_length=100),
                user: User = Depends(rate_limited), db: Session = Depends(get_db)):
    role = role or ((user.profile.target_roles or [None])[0] if user.profile else None)
    if not role:
        raise AppError("Give a role, or set a target role in your profile.", code="validation_error",
                       status_code=422)
    return build_path(role, resume_skills(user), progress_of(db, user))


@router.put("/career/progress", response_model=dict[str, str])
def set_progress(body: SkillStatusIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(SkillProgress).where(SkillProgress.user_id == user.id, SkillProgress.skill == body.skill))
    if row is None:
        db.add(SkillProgress(user_id=user.id, skill=body.skill, status=body.status))
    else:
        row.status = body.status
    db.commit()
    return progress_of(db, user)


@router.post("/github/analyse", response_model=GitHubReport)
def github(body: GitHubIn, user: User = Depends(rate_limited), db: Session = Depends(get_db)):
    report = analyse(body.username, resume_skills(user))
    if user.profile is not None and user.profile.github_username != report.username:
        user.profile.github_username = report.username  # remembered for the chat ("review my GitHub")
        db.commit()
    return report
