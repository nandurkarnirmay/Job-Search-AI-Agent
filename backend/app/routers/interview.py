from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, rate_limited
from app.domain import InterviewQuestion
from app.errors import AppError
from app.models import InterviewSession, User
from app.schemas import AnswerIn, AnswerOut, InterviewIn, InterviewOut
from app.services.interview import create_session, evaluate_answer, interview_out
from app.services.search_service import get_job

router = APIRouter(prefix="/interview", tags=["interview"])


def _own(db: Session, user: User, sid: int) -> InterviewSession:
    s = db.get(InterviewSession, sid)
    if s is None or s.user_id != user.id:
        raise AppError("Interview session not found.", code="not_found", status_code=404)
    return s


@router.post("/sessions", response_model=InterviewOut, status_code=201)
def new_session(body: InterviewIn, user: User = Depends(rate_limited), db: Session = Depends(get_db)):
    role, company, description = body.role, body.company, ""
    if body.job_id and (job := get_job(body.job_id)):
        role, company, description = role or job.title, company or job.company, job.description
    if not role:
        raise AppError("Give a role, or a job_id from a recent search.", code="validation_error", status_code=422)
    s, notes = create_session(db, user, role, company, description)
    return interview_out(s, notes)


@router.get("/sessions", response_model=list[InterviewOut])
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(InterviewSession).where(InterviewSession.user_id == user.id)
                      .order_by(InterviewSession.id.desc()).limit(20)).all()
    return [interview_out(s) for s in rows]


@router.get("/sessions/{sid}", response_model=InterviewOut)
def get_session(sid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return interview_out(_own(db, user, sid))


@router.post("/sessions/{sid}/questions/{qid}/answer", response_model=AnswerOut)
def answer(sid: int, qid: str, body: AnswerIn, user: User = Depends(rate_limited), db: Session = Depends(get_db)):
    s = _own(db, user, sid)
    q = next((InterviewQuestion(**q) for q in s.questions if q["id"] == qid), None)
    if q is None:
        raise AppError("Question not found.", code="not_found", status_code=404)
    fb = evaluate_answer(q, body.answer, s.company)
    s.answers = {**(s.answers or {}), qid: {"answer": body.answer, "feedback": fb.model_dump()}}
    db.commit()
    return AnswerOut(question_id=qid, feedback=fb)


@router.delete("/sessions/{sid}", status_code=204)
def delete_session(sid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own(db, user, sid))
    db.commit()
