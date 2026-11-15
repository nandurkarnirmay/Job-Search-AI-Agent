from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, rate_limited
from app.domain import ATSMatch, ResumeReview
from app.errors import AppError
from app.models import Resume, User
from app.schemas import MatchIn, ResumeOut
from app.services.resume_analysis import ats_match, review_for_role
from app.services.resume_parser import MAX_BYTES, ResumeError, from_row, parse_resume
from app.services.search_service import get_job

router = APIRouter(prefix="/resume", tags=["resume"])


def _out(r: Resume) -> ResumeOut:
    return ResumeOut.model_validate(r, from_attributes=True)


def require_resume(user: User) -> Resume:
    if user.resume is None:
        raise AppError("Upload your resume first (Resume page).", code="no_resume", status_code=404)
    return user.resume


@router.post("", response_model=ResumeOut, status_code=201)
async def upload(file: UploadFile = File(...), user: User = Depends(rate_limited), db: Session = Depends(get_db)):
    data = await file.read(MAX_BYTES + 1)  # never read more than the limit into memory
    if len(data) > MAX_BYTES:
        raise ResumeError("File is larger than 2 MB.")
    parsed = parse_resume(file.filename or "resume", data)
    if user.resume is not None:
        db.delete(user.resume)
        db.flush()
    user.resume = Resume(filename=(file.filename or "resume")[:200], kind=parsed.kind, pages=parsed.pages,
                         text=parsed.text, word_count=parsed.word_count, skills=parsed.skills,
                         sections=parsed.sections, has_contact=parsed.has_contact, warnings=parsed.warnings)
    db.commit()
    return _out(user.resume)


@router.get("", response_model=ResumeOut)
def get_resume(user: User = Depends(get_current_user)):
    return _out(require_resume(user))


@router.delete("", status_code=204)
def delete_resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(require_resume(user))
    db.commit()


@router.post("/match", response_model=ATSMatch)
def match(body: MatchIn, user: User = Depends(rate_limited)):
    resume = from_row(require_resume(user))
    if body.job_id:
        job = get_job(body.job_id)
        if job is None:
            raise AppError("That job is no longer in recent results; search again or paste the description.",
                           code="job_expired", status_code=404)
        return ats_match(resume, job.title, job.description, job.company)
    if not (body.job_title and body.description and len(body.description) >= 50):
        raise AppError("Give a job_id, or a job title plus the job description (50+ characters).",
                       code="validation_error", status_code=422)
    return ats_match(resume, body.job_title, body.description, body.company)


@router.get("/review", response_model=ResumeReview)
def review(role: str | None = Query(default=None, min_length=2, max_length=100), user: User = Depends(rate_limited)):
    role = role or ((user.profile.target_roles or [None])[0] if user.profile else None)
    return review_for_role(from_row(require_resume(user)), role)
