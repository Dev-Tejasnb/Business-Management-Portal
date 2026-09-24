"""Centralized audit logging service.

All important actions (especially security events) are recorded through this
service. Audit records are append-only: there are no application endpoints that
update or delete them. The service writes through its own session so an audit
record persists even when the originating request fails (e.g. a failed login).
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.core.logging import get_logger
from app.models.audit_log import AuditLog

logger = get_logger(__name__)

#: Namespace of actions defined here for consistent audit terminology.
class AuditAction:
    LOGIN_SUCCESS = "login.success"
    LOGIN_FAILURE = "login.failure"
    LOGOUT = "logout"
    SESSION_REVOKED = "session.revoked"
    PASSWORD_CHANGE = "password.change"
    ACCOUNT_ACTIVATED = "account.activated"
    ACCOUNT_DEACTIVATED = "account.deactivated"


class Module:
    AUTH = "auth"
    SHOP = "shop"
    MEMBERSHIP = "membership"
    USER = "user"
    SERVICE = "service"
    CUSTOMER = "customer"
    APPLICATION = "application"
    DOCUMENT = "document"


def request_audit_context(request: Request) -> tuple[str | None, str | None]:
    """Extract the client IP and user agent for audit correlation."""
    ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    user_agent = request.headers.get("user-agent")
    return ip, user_agent


class AuditService:
    """Append-only audit writer. Safe to reuse as a singleton."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._factory = session_factory or get_session_factory()

    async def record(
        self,
        *,
        action: str,
        module: str,
        actor_user_id: int | None = None,
        actor_role: str | None = None,
        shop_id: int | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """Persist an audit record. If session is provided, use it; otherwise create a new transaction."""
        entry = AuditLog(
            action=action,
            module=module,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_values=old_values,
            new_values=new_values,
            extra=extra,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if session is not None:
            # Use the provided session (caller manages transaction)
            session.add(entry)
            await session.flush()
        else:
            # Create own transaction for append-only persistence
            async with self._factory() as own_session:
                own_session.add(entry)
                await own_session.commit()

        logger.debug("Audit recorded module=%s action=%s", module, action)

    async def record_from_request(
        self,
        request: Request,
        *,
        action: str,
        module: str,
        actor_user_id: int | None = None,
        actor_role: str | None = None,
        shop_id: int | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        ip, user_agent = request_audit_context(request)
        await self.record(
            action=action,
            module=module,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            extra=extra,
            ip_address=ip,
            user_agent=user_agent,
        )


audit_service = AuditService()


def get_audit_service() -> AuditService:
    """FastAPI dependency exposing the shared audit service."""
    return audit_service