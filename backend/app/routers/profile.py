from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Profile, User
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/me/profile", tags=["profile"])


def _get_or_create(user: User, db: Session) -> Profile:
    if user.profile is None:
        user.profile = Profile()
        db.commit()
    return user.profile


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ProfileOut.model_validate(_get_or_create(user, db), from_attributes=True)


@router.put("", response_model=ProfileOut)
def update_profile(body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _get_or_create(user, db)
    data = body.model_dump()
    data["preferred_cities"] = [c.strip() for c in data["preferred_cities"] if c.strip()]
    data["skills"] = sorted({s.strip().lower() for s in data["skills"] if s.strip()})
    roles: dict[str, str] = {}
    for r in data["target_roles"]:
        if r.strip():
            roles.setdefault(r.strip().lower(), r.strip())  # case-insensitive dedupe, keep first spelling
    data["target_roles"] = list(roles.values())
    for key, value in data.items():
        setattr(profile, key, value)
    db.commit()
    return ProfileOut.model_validate(profile, from_attributes=True)


def profile_defaults(profile: Profile | None) -> dict:
    """Profile values the chat agent may use when the message doesn't say them."""
    if profile is None:
        return {}
    d = {}
    if profile.target_roles:
        d["keywords"] = profile.target_roles[0]  # "show me jobs" searches the user's main target role
    city = (profile.preferred_cities or [None])[0] or profile.current_city
    if city:
        d["city"] = city
    if profile.experience_years is not None:
        d["max_experience_years"] = profile.experience_years
    if profile.work_mode and profile.work_mode != "any":
        d["work_mode"] = profile.work_mode
    if profile.notice_period_days is not None:
        d["notice_period_days"] = profile.notice_period_days
    return d
