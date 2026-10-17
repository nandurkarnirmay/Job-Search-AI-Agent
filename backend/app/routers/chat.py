from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.graph import run_agent
from app.db import get_db
from app.deps import rate_limited
from app.models import User
from app.routers.profile import profile_defaults
from app.schemas import ChatIn, ChatOut
from app.services.search_service import record

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatOut)
def chat(body: ChatIn, user: User = Depends(rate_limited), db: Session = Depends(get_db)):
    state = run_agent(body.message, profile_defaults(user.profile))
    outcome = state.get("outcome")
    if outcome is not None:
        record(db, outcome, user_id=user.id, channel="chat", query=body.message)
    return ChatOut(reply=state["reply"], params=state.get("params"),
                   jobs=outcome.jobs[:20] if outcome else [], parser=state.get("parser", "rules"))
