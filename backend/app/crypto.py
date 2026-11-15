"""Field-level encryption at rest for personal free text: resume text, interview answers, chat messages, notes.

FIELD_ENCRYPTION_KEYS is a comma-separated list of secrets (any long random strings). The first encrypts; all
of them decrypt, so a key can be rotated by putting the new one first and re-saving data over time. Each
secret is turned into a Fernet key (AES-128-CBC + HMAC-SHA256) with SHA-256. Values written before encryption
was enabled (plain text / plain JSON) are still readable and get encrypted the next time they're saved."""
import base64
import hashlib
import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import JSON, Text
from sqlalchemy.types import TypeDecorator

from app.config import get_settings

PREFIX = "enc:v1:"
JSON_KEY = "_enc"


@lru_cache
def _fernet() -> MultiFernet:
    s = get_settings()
    secrets = [k.strip() for k in s.field_encryption_keys.split(",") if k.strip()] or [f"dev-only:{s.jwt_secret}"]
    return MultiFernet([Fernet(base64.urlsafe_b64encode(hashlib.sha256(k.encode()).digest())) for k in secrets])


def encrypt(text: str) -> str:
    return PREFIX + _fernet().encrypt(text.encode()).decode()


def decrypt(value: str) -> str:
    if not value.startswith(PREFIX):
        return value  # legacy plain text
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken as e:
        raise RuntimeError("Can't decrypt a stored field: FIELD_ENCRYPTION_KEYS is missing the key it was "
                           "written with.") from e


class EncryptedText(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else encrypt(value)

    def process_result_value(self, value, dialect):
        return None if value is None else decrypt(value)


class EncryptedJSON(TypeDecorator):
    """Stored as {"_enc": "<token>"} so the column stays valid JSON on Postgres."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else {JSON_KEY: encrypt(json.dumps(value))}

    def process_result_value(self, value, dialect):
        if isinstance(value, dict) and set(value) == {JSON_KEY}:
            return json.loads(decrypt(value[JSON_KEY]))
        return value  # legacy plain JSON
