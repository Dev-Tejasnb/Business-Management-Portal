"""Tests for centralized audit logging."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.database import get_session_factory
from app.models.audit_log import AuditLog


async def _count_audit(action: str) -> int:
    """Count audit logs for a given action using a fresh session.

    This helper uses the global session factory, which is initialized once per
    test session. All calls within a test run on the same event loop context.
    """
    factory = get_session_factory()
    async with factory() as session:
        result = await session.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == action)
        )
        return result or 0


async def test_login_success_is_audited(client: AsyncClient, create_user) -> None:
    await create_user("alice@example.com")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "Password123!"}
    )
    assert resp.status_code == 200
    count = await _count_audit("login.success")
    assert count == 1, f"Expected 1 login.success audit log, got {count}"


async def test_login_failure_is_audited(client: AsyncClient, create_user) -> None:
    await create_user("alice@example.com")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "WrongPass1"}
    )
    assert resp.status_code == 401
    assert await _count_audit("login.failure") == 1


async def test_logout_is_audited(client: AsyncClient, create_user, login) -> None:
    await create_user("alice@example.com")
    await login("alice@example.com")
    assert (await client.post("/api/v1/auth/logout")).status_code == 200
    assert await _count_audit("logout") == 1


async def test_audit_log_does_not_store_passwords(client: AsyncClient, create_user) -> None:
    await create_user("alice@example.com")
    await client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "Password123!"}
    )
    factory = get_session_factory()
    async with factory() as session:
        rows = (await session.scalars(select(AuditLog))).all()
    assert rows
    serialized = [str(r.extra) for r in rows] + [str(r.new_values) for r in rows]
    assert all("Password123!" not in s for s in serialized)


async def test_audit_log_has_no_public_crud_endpoints(client: AsyncClient) -> None:
    # There is intentionally no route to read/modify/delete audit history.
    assert (await client.get("/api/v1/audit-logs")).status_code == 404
    assert (await client.get("/api/v1/audit-logs/1")).status_code == 404