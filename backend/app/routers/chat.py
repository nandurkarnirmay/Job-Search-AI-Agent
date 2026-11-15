import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.graph import ToolContext, run_agent
from app.db import get_db
from app.deps import get_current_user, rate_limited
from app.domain import SearchParams
from app.errors import AppError
from app.models import ChatMessage, ChatThread, User
from app.routers.profile import profile_defaults
from app.schemas import ChatExtras, ChatIn, ChatOut, MessageOut, ThreadOut, ThreadSummary
from app.services.search_service import record

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_MESSAGES = 6
REMEMBERED_JOBS = 10


def _own_thread(db: Session, user: User, thread_id: str) -> ChatThread:
    thread = db.get(ChatThread, thread_id)
    if thread is None or thread.user_id != user.id:
        raise AppError("Conversation not found.", code="not_found", status_code=404)
    return thread


def _compact(job) -> dict:
    return {"id": job.id, "title": job.title, "company": job.company, "location": job.location, "url": job.url}


@router.post("", response_model=ChatOut)
def chat(body: ChatIn, user: User = Depends(rate_limited), db: Session = Depends(get_db)):
    if body.thread_id:
        thread = _own_thread(db, user, body.thread_id)
    else:
        thread = ChatThread(id=uuid.uuid4().hex, user_id=user.id, title=body.message[:80])
        db.add(thread)
        db.commit()  # persist first: a failed analytics write later must not roll back the conversation

    history = [{"role": m.role, "content": m.content} for m in thread.messages[-HISTORY_MESSAGES:]]
    context = {"last_params": SearchParams(**thread.last_params) if thread.last_params else None,
               "last_jobs": thread.last_jobs or [], "history": history}
    state = run_agent(body.message, profile_defaults(user.profile), context, tools=ToolContext(db=db, user=user))

    outcome, company, salary = state.get("outcome"), state.get("company"), state.get("salary")
    jobs = outcome.jobs[:20] if outcome else []
    if outcome is not None:
        record(db, outcome, user_id=user.id, channel="chat", query=body.message)
        thread.last_params = outcome.params.model_dump(exclude_none=True)
        thread.last_jobs = [_compact(j) for j in jobs[:REMEMBERED_JOBS]]

    payload = {"params": state["params"].model_dump(exclude_none=True) if state.get("params") else None,
               "jobs": [j.model_dump(exclude={"description"}) for j in jobs],
               "company": company.model_dump() if company else None,
               "salary": salary.model_dump() if salary else None,
               "extras": state.get("extras")}
    thread.updated_at = datetime.now(timezone.utc)  # adding messages alone doesn't trigger onupdate
    db.add_all([ChatMessage(thread=thread, role="user", content=body.message),
                ChatMessage(thread=thread, role="assistant", content=state["reply"], intent=state["intent"],
                            payload=payload)])
    db.commit()

    return ChatOut(thread_id=thread.id, reply=state["reply"], intent=state["intent"], params=state.get("params"),
                   jobs=jobs, company=company, salary=salary,
                   extras=ChatExtras(**state["extras"]) if state.get("extras") else None,
                   parser="llm" if state.get("llm_used") else "rules")


@router.get("/threads", response_model=list[ThreadSummary])
def list_threads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(ChatThread).where(ChatThread.user_id == user.id)
                      .order_by(ChatThread.updated_at.desc()).limit(30)).all()
    return [ThreadSummary(id=t.id, title=t.title, updated_at=t.updated_at) for t in rows]


@router.get("/threads/{thread_id}", response_model=ThreadOut)
def get_thread(thread_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = _own_thread(db, user, thread_id)
    return ThreadOut(id=t.id, title=t.title, updated_at=t.updated_at,
                     messages=[MessageOut.model_validate(m, from_attributes=True) for m in t.messages])


@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(thread_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own_thread(db, user, thread_id))
    db.commit()
