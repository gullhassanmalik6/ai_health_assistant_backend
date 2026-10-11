"""Secure one-time codes. Only hashes are stored."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from app.core.config import settings
from app.core.constants import VERIFICATION_CODE_LENGTH


def generate_verification_code(length: int = VERIFICATION_CODE_LENGTH) -> str:
    upper = 10**length
    return f"{secrets.randbelow(upper):0{length}d}"


def hash_verification_code(code: str, email: str) -> str:
    secret = settings.APP_SECRET_KEY.encode("utf-8")
    payload = f"{email.strip().lower()}:{code.strip()}".encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def codes_match(code: str, email: str, stored_hash: str) -> bool:
    expected = hash_verification_code(code, email)
    return hmac.compare_digest(expected, stored_hash)
