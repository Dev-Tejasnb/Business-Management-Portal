"""Authentication business logic.

Handles credential verification and the access/refresh token lifecycle. Cookie
handling and audit recording are orchestrated by the router.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    refresh_token_ttl_seconds,
    verify_password,
)
from app.core.session import SessionStore
from app.models.user import User


class AuthService:
    """Verifies credentials and manages the token/session lifecycle."""

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> User | None:
        """Return the user if credentials are valid and the account is active."""
        user = await db.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def issue_tokens(self, store: SessionStore, user: User) -> tuple[str, str, int]:
        """Create an access token and a new refresh session.

        Returns (access_token, refresh_token, refresh_ttl_seconds).
        """
        access_token = create_access_token(subject=str(user.id))
        refresh_token, ttl = await store.create(user.id)
        return access_token, refresh_token, ttl

    async def rotate_session(
        self, store: SessionStore, refresh_token: str
    ) -> tuple[str, str, int, int] | None:
        """Rotate a refresh session: revoke the old token and issue a new pair.

        Returns (access_token, new_refresh_token, ttl, user_id) or None if the
        token is invalid/expired/revoked.
        """
        user_id = await store.validate(refresh_token)
        if user_id is None:
            return None
        await store.revoke(refresh_token)
        new_refresh, ttl = await store.create(user_id)
        access_token = create_access_token(subject=str(user_id))
        return access_token, new_refresh, ttl, user_id

    async def revoke_session(self, store: SessionStore, refresh_token: str) -> bool:
        """Revoke a refresh session (logout)."""
        return await store.revoke(refresh_token)

    @staticmethod
    def refresh_ttl_seconds() -> int:
        return refresh_token_ttl_seconds()


auth_service = AuthService()