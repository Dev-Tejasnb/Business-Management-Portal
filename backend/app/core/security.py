"""Security primitives: Argon2id password hashing, JWT access tokens and
refresh-token generation.

- Passwords are hashed with Argon2id (never stored in plaintext).
- Access tokens are short-lived signed JWTs (held in memory by the client).
- Refresh tokens are opaque random values; their server-side session lifecycle
  is managed by ``app.core.session`` (Redis-backed), not embedded in the token.

Centralized password rules live here so all modules enforce the same policy.
"""

from __future__ import annotations

import secrets
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_password_hasher = PasswordHasher()

# Centralized password policy.
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class PasswordPolicyError(ValueError):
    """Raised when a password does not meet the centralized policy."""


# ---------------------------------------------------------------------------
# Password hashing (Argon2id)
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    validate_password_policy(password)
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against an Argon2id hash. Never leaks why it failed."""
    try:
        return _password_hasher.verify(hashed, password)
    except (VerificationError, VerifyMismatchError, InvalidHashError, Argon2Error, Exception):
        return False


def validate_password_policy(password: str) -> None:
    """Validate a password against the centralized policy. Raises on violation."""
    if not isinstance(password, str):
        raise PasswordPolicyError("Password must be a string.")
    if not (PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH):
        raise PasswordPolicyError(
            f"Password must be between {PASSWORD_MIN_LENGTH} and "
            f"{PASSWORD_MAX_LENGTH} characters."
        )
    if not any(c.islower() for c in password):
        raise PasswordPolicyError("Password must contain a lowercase letter.")
    if not any(c.isupper() for c in password):
        raise PasswordPolicyError("Password must contain an uppercase letter.")
    if not any(c.isdigit() for c in password):
        raise PasswordPolicyError("Password must contain a digit.")


# ---------------------------------------------------------------------------
# Access tokens (JWT)
# ---------------------------------------------------------------------------
def create_access_token(*, subject: str, token_type: str = "access") -> str:
    """Create a short-lived JWT access token.

    ``subject`` should be the user id as a string. Includes ``type`` so access
    tokens can never be confused with other token kinds.
    """
    settings = get_settings()
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises ``jwt.PyJWTError`` for invalid/expired/malformed tokens; callers turn
    this into an ``UnauthorizedError`` without leaking details.
    """
    settings = get_settings()
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token.")
    return payload


# ---------------------------------------------------------------------------
# Refresh tokens (opaque, stored server-side)
# ---------------------------------------------------------------------------
def generate_refresh_token() -> str:
    """Generate a cryptographically random opaque refresh token."""
    return secrets.token_urlsafe(48)


def refresh_token_ttl_seconds() -> int:
    """Return the refresh session lifetime in seconds."""
    from datetime import timedelta

    return int(timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())


def access_token_ttl_seconds() -> int:
    """Return the access token lifetime in seconds."""
    return get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60