from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings
from app.errors import AuthError

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes; truncate explicitly so behaviour is predictable.
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=s.jwt_expire_minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError as e:
        raise AuthError("Session expired. Please log in again.", code="token_expired") from e
    except (jwt.InvalidTokenError, KeyError, ValueError) as e:
        raise AuthError("Invalid authentication token.") from e
