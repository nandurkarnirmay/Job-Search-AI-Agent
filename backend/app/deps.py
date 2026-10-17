from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import AppError, AuthError
from app.models import User
from app.ratelimit import check_rate_limit
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise AuthError("Log in to continue.")
    user = db.get(User, decode_access_token(creds.credentials))
    if user is None:
        raise AuthError("Account no longer exists.")
    return user


def rate_limited(request: Request, user: User = Depends(get_current_user)) -> User:
    check_rate_limit(f"user:{user.id}:{request.url.path}")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.email.lower() not in get_settings().admin_email_set:
        raise AppError("Admins only.", code="forbidden", status_code=403)
    return user
