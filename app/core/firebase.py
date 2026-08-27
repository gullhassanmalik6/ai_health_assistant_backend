"""Firebase Admin SDK initialization and Identity Toolkit helpers.

Firebase Authentication is the identity provider. This module:
- initializes the Admin SDK once per process
- verifies ID tokens
- performs email/password, anonymous, reset, and refresh operations via REST

Passwords are never stored in PostgreSQL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import firebase_admin
import httpx
from firebase_admin import auth, credentials
from firebase_admin.auth import (
    ExpiredIdTokenError,
    InvalidIdTokenError,
    RevokedIdTokenError,
    UserDisabledError,
    UserNotFoundError,
)

from app.core.config import settings
from app.core.constants import (
    FIREBASE_ACCOUNT_LOOKUP_URL,
    FIREBASE_OOB_URL,
    FIREBASE_PROVIDER_MAP,
    FIREBASE_RESET_PASSWORD_URL,
    FIREBASE_SIGN_IN_URL,
    FIREBASE_SIGN_UP_URL,
    FIREBASE_TOKEN_URL,
    AuthProvider,
    ErrorCode,
)
from app.core.exceptions import AuthenticationError, ConflictError, FirebaseServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

_firebase_app: firebase_admin.App | None = None
_http_client: httpx.AsyncClient | None = None


@dataclass(frozen=True, slots=True)
class FirebaseTokenClaims:
    uid: str
    email: str | None
    name: str | None
    email_verified: bool
    provider: AuthProvider
    auth_time: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FirebaseSession:
    uid: str
    email: str | None
    id_token: str
    refresh_token: str | None
    expires_in: int
    email_verified: bool
    is_anonymous: bool
    display_name: str | None = None


def _build_certificate() -> credentials.Base:
    if settings.FIREBASE_CREDENTIALS_PATH:
        return credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)

    if settings.FIREBASE_CREDENTIALS_JSON:
        data = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
        return credentials.Certificate(data)

    if not (
        settings.FIREBASE_PROJECT_ID
        and settings.FIREBASE_CLIENT_EMAIL
        and settings.FIREBASE_PRIVATE_KEY
    ):
        raise RuntimeError(
            "Firebase credentials are not configured. Set FIREBASE_CREDENTIALS_PATH "
            "or FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY."
        )

    return credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.FIREBASE_PROJECT_ID,
            "private_key": settings.FIREBASE_PRIVATE_KEY,
            "client_email": settings.FIREBASE_CLIENT_EMAIL,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )


def init_firebase() -> firebase_admin.App | None:
    """Initialize Firebase Admin once. Skipped in the test environment."""
    global _firebase_app

    if settings.is_test:
        logger.info("Skipping Firebase Admin initialization in test environment.")
        return None

    if _firebase_app is not None:
        return _firebase_app

    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    try:
        cred = _build_certificate()
        options = {"projectId": settings.FIREBASE_PROJECT_ID} if settings.FIREBASE_PROJECT_ID else None
        _firebase_app = firebase_admin.initialize_app(cred, options)
        logger.info("Firebase Admin SDK initialized.")
        return _firebase_app
    except Exception as exc:
        logger.warning(
            "Firebase Admin SDK was not initialized (%s). Auth endpoints will fail until credentials are valid.",
            type(exc).__name__,
        )
        _firebase_app = None
        return None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS)
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


def map_sign_in_provider(firebase_provider: str | None) -> AuthProvider:
    if not firebase_provider:
        return AuthProvider.EMAIL
    return FIREBASE_PROVIDER_MAP.get(firebase_provider, AuthProvider.EMAIL)


def parse_token_claims(decoded: dict[str, Any]) -> FirebaseTokenClaims:
    firebase_info = decoded.get("firebase") or {}
    provider = map_sign_in_provider(firebase_info.get("sign_in_provider"))
    return FirebaseTokenClaims(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        email_verified=bool(decoded.get("email_verified", False)),
        provider=provider,
        auth_time=decoded.get("auth_time"),
        raw=decoded,
    )


def verify_id_token(id_token: str, *, check_revoked: bool = True) -> FirebaseTokenClaims:
    """Verify a Firebase ID token. Identity is derived only from the verified token."""
    if not id_token or not id_token.strip():
        raise AuthenticationError(
            "Missing authentication token.",
            error_code=ErrorCode.AUTH_TOKEN_MISSING,
        )

    try:
        decoded = auth.verify_id_token(id_token, check_revoked=check_revoked)
    except ExpiredIdTokenError as exc:
        raise AuthenticationError(
            "Authentication token has expired.",
            error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
        ) from exc
    except RevokedIdTokenError as exc:
        raise AuthenticationError(
            "Authentication token has been revoked.",
            error_code=ErrorCode.AUTH_SESSION_REVOKED,
        ) from exc
    except UserDisabledError as exc:
        raise AuthenticationError(
            "This account has been disabled.",
            error_code=ErrorCode.AUTH_ACCOUNT_DISABLED,
        ) from exc
    except InvalidIdTokenError as exc:
        raise AuthenticationError(
            "Invalid authentication token.",
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
        ) from exc
    except Exception as exc:  # noqa: BLE001 — map unknown verifier failures to 401
        logger.warning("Firebase token verification failed: %s", type(exc).__name__)
        raise AuthenticationError(
            "Invalid authentication token.",
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
        ) from exc

    if "uid" not in decoded:
        raise AuthenticationError(
            "Invalid authentication token.",
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
        )
    return parse_token_claims(decoded)


def _rest_url(base: str) -> str:
    if not settings.FIREBASE_API_KEY:
        raise FirebaseServiceError("Firebase API key is not configured.")
    return f"{base}?key={settings.FIREBASE_API_KEY}"


def _map_firebase_rest_error(payload: dict[str, Any]) -> Exception:
    message = ((payload.get("error") or {}).get("message") or "").upper()

    if "EMAIL_EXISTS" in message:
        return ConflictError(
            "An account with this email already exists.",
            error_code=ErrorCode.AUTH_ACCOUNT_EXISTS,
        )
    if any(code in message for code in ("EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS", "USER_NOT_FOUND")):
        return AuthenticationError(
            "Invalid email or password.",
            error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
        )
    if "USER_DISABLED" in message:
        return AuthenticationError(
            "This account has been disabled.",
            error_code=ErrorCode.AUTH_ACCOUNT_DISABLED,
        )
    if "WEAK_PASSWORD" in message:
        return AuthenticationError(
            "Password does not meet security requirements.",
            error_code=ErrorCode.AUTH_WEAK_PASSWORD,
        )
    if "TOO_MANY_ATTEMPTS" in message:
        from app.core.exceptions import RateLimitError

        return RateLimitError()
    if "INVALID_ID_TOKEN" in message or "TOKEN_EXPIRED" in message:
        return AuthenticationError(
            "Invalid authentication token.",
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
        )
    if "INVALID_OOB_CODE" in message or "EXPIRED_OOB_CODE" in message:
        return AuthenticationError(
            "This password reset link is invalid or has expired.",
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
        )

    logger.warning("Unhandled Firebase identity error category=%s", message[:80] or "unknown")
    return FirebaseServiceError("Identity service request failed.")


async def _post_identity(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = get_http_client()
    try:
        response = await client.post(url, json=payload)
    except httpx.HTTPError as exc:
        logger.error("Firebase identity HTTP failure: %s", type(exc).__name__)
        raise FirebaseServiceError("Identity service is temporarily unavailable.") from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.is_error:
        raise _map_firebase_rest_error(data)
    return data


def _session_from_auth_payload(data: dict[str, Any], *, is_anonymous: bool = False) -> FirebaseSession:
    expires_raw = data.get("expiresIn") or data.get("expires_in") or "3600"
    try:
        expires_in = int(expires_raw)
    except (TypeError, ValueError):
        expires_in = 3600

    return FirebaseSession(
        uid=data.get("localId") or data.get("user_id") or "",
        email=data.get("email"),
        id_token=data.get("idToken") or data.get("id_token") or "",
        refresh_token=data.get("refreshToken") or data.get("refresh_token"),
        expires_in=expires_in,
        email_verified=bool(data.get("emailVerified", False)),
        is_anonymous=is_anonymous,
        display_name=data.get("displayName"),
    )


async def sign_up_with_email(email: str, password: str, display_name: str | None = None) -> FirebaseSession:
    payload: dict[str, Any] = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    if display_name:
        payload["displayName"] = display_name
    data = await _post_identity(_rest_url(FIREBASE_SIGN_UP_URL), payload)
    session = _session_from_auth_payload(data, is_anonymous=False)
    if display_name and session.uid:
        try:
            auth.update_user(session.uid, display_name=display_name)
        except Exception:  # noqa: BLE001
            logger.info("Display name update skipped after registration.")
    return session


async def sign_in_with_email(email: str, password: str) -> FirebaseSession:
    data = await _post_identity(
        _rest_url(FIREBASE_SIGN_IN_URL),
        {"email": email, "password": password, "returnSecureToken": True},
    )
    return _session_from_auth_payload(data, is_anonymous=False)


async def sign_in_anonymously() -> FirebaseSession:
    data = await _post_identity(
        _rest_url(FIREBASE_SIGN_UP_URL),
        {"returnSecureToken": True},
    )
    return _session_from_auth_payload(data, is_anonymous=True)


async def send_password_reset_email(email: str) -> None:
    """Always succeed from the caller's perspective. Existence is not leaked."""
    try:
        await _post_identity(
            _rest_url(FIREBASE_OOB_URL),
            {"requestType": "PASSWORD_RESET", "email": email},
        )
    except (AuthenticationError, ConflictError, FirebaseServiceError):
        logger.info("Password reset requested.")
    except Exception:  # noqa: BLE001
        logger.info("Password reset requested.")


async def confirm_password_reset(oob_code: str, new_password: str) -> None:
    await _post_identity(
        _rest_url(FIREBASE_RESET_PASSWORD_URL),
        {"oobCode": oob_code, "newPassword": new_password},
    )


async def send_email_verification(id_token: str) -> None:
    await _post_identity(
        _rest_url(FIREBASE_OOB_URL),
        {"requestType": "VERIFY_EMAIL", "idToken": id_token},
    )


async def refresh_id_token(refresh_token: str) -> FirebaseSession:
    payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    client = get_http_client()
    try:
        response = await client.post(_rest_url(FIREBASE_TOKEN_URL), data=payload)
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Firebase token refresh failed: %s", type(exc).__name__)
        raise FirebaseServiceError("Identity service is temporarily unavailable.") from exc

    if response.is_error:
        raise _map_firebase_rest_error(data)
    return _session_from_auth_payload(data, is_anonymous=False)


async def lookup_account(id_token: str) -> dict[str, Any]:
    data = await _post_identity(
        _rest_url(FIREBASE_ACCOUNT_LOOKUP_URL),
        {"idToken": id_token},
    )
    users = data.get("users") or []
    return users[0] if users else {}


def delete_firebase_user(uid: str) -> None:
    try:
        auth.delete_user(uid)
    except UserNotFoundError:
        logger.info("Firebase identity already absent during account deletion.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to delete Firebase identity: %s", type(exc).__name__)
        raise FirebaseServiceError("Failed to delete identity.") from exc


def get_firebase_user(uid: str) -> auth.UserRecord | None:
    try:
        return auth.get_user(uid)
    except UserNotFoundError:
        return None
