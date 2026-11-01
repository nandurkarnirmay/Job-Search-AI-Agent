from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models import Application, User
from app.schemas import ApplicationIn, ApplicationOut, ApplicationPatch, AppStatus
from app.services.applications import add_application, pipeline, set_status

router = APIRouter(prefix="/applications", tags=["applications"])


def _own(db: Session, user: User, app_id: int) -> Application:
    a = db.get(Application, app_id)
    if a is None or a.user_id != user.id:
        raise AppError("Application not found.", code="not_found", status_code=404)
    return a


def _out(a: Application) -> ApplicationOut:
    return ApplicationOut.model_validate(a, from_attributes=True)


@router.get("", response_model=list[ApplicationOut])
def list_applications(status: AppStatus | None = Query(default=None), user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    q = select(Application).where(Application.user_id == user.id)
    if status:
        q = q.where(Application.status == status)
    return [_out(a) for a in db.scalars(q.order_by(Application.updated_at.desc())).all()]


@router.get("/pipeline", response_model=dict[str, int])
def get_pipeline(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return pipeline(db, user.id)


@router.post("", response_model=ApplicationOut, status_code=201)
def create(body: ApplicationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(add_application(db, user.id, **body.model_dump()))


@router.patch("/{app_id}", response_model=ApplicationOut)
def update(app_id: int, body: ApplicationPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = _own(db, user, app_id)
    data = body.model_dump(exclude_unset=True)
    if status := data.pop("status", None):
        set_status(a, status)
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    return _out(a)


@router.delete("/{app_id}", status_code=204)
def delete(app_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own(db, user, app_id))
    db.commit()
