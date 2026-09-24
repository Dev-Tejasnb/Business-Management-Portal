"""Tests for Audit Logging in Phase 3 (Shop & Staff operations)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from app.core.roles import PlatformRole, ShopRole
from app.models import Shop, User
from app.models.audit_log import AuditLog
from app.models.membership import ShopMembership
from app.models.shop import ShopStatus


async def get_audit_logs(db_factory, *, action: str = None, module: str = None, shop_id: int = None):
    """Helper to fetch audit logs."""
    async with db_factory() as session:
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if module:
            query = query.where(AuditLog.module == module)
        if shop_id:
            query = query.where(AuditLog.shop_id == shop_id)
        query = query.order_by(AuditLog.created_at.desc())
        result = await session.scalars(query)
        return list(result.all())


async def test_audit_shop_create(client: AsyncClient, login, create_user, create_shop) -> None:
    """Audit logs created for shop creation."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    await login("owner@example.com")

    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Audit Shop", "slug": "audit-shop"},
    )
    assert resp.status_code == 201
    shop_id = resp.json()["id"]

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), action="shop.created", module="shop")
    assert len(logs) >= 1
    log = logs[0]
    assert log.action == "shop.created"
    assert log.module == "shop"
    assert log.entity_type == "shop"
    assert log.entity_id == str(shop_id)
    assert "code" in log.new_values
    assert "name" in log.new_values
    assert "slug" in log.new_values


async def test_audit_shop_update(client: AsyncClient, login, create_user, create_shop) -> None:
    """Audit logs created for shop update."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    await login("owner@example.com")

    # Create shop
    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Audit Shop", "slug": "audit-shop"},
    )
    assert resp.status_code == 201
    shop_id = resp.json()["id"]

    # Update shop
    resp = await client.patch(
        f"/api/v1/platform/shops/{shop_id}",
        json={"name": "Updated Shop Name"},
    )
    assert resp.status_code == 200

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), action="shop.updated", module="shop", shop_id=shop_id)
    assert len(logs) >= 1
    log = logs[0]
    assert log.action == "shop.updated"
    assert log.module == "shop"
    assert log.entity_type == "shop"
    assert log.entity_id == str(shop_id)
    assert "name" in log.old_values
    assert "name" in log.new_values


async def test_audit_shop_activate_deactivate(client: AsyncClient, login, create_user, create_shop) -> None:
    """Audit logs created for shop activate/deactivate."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    await login("owner@example.com")

    # Create shop
    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Audit Shop", "slug": "audit-shop"},
    )
    assert resp.status_code == 201
    shop_id = resp.json()["id"]

    # Deactivate
    resp = await client.post(
        f"/api/v1/platform/shops/{shop_id}/deactivate",
        json={"status": "inactive"},
    )
    assert resp.status_code == 200

    # Activate
    resp = await client.post(
        f"/api/v1/platform/shops/{shop_id}/activate",
        json={},
    )
    assert resp.status_code == 200

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), module="shop", shop_id=shop_id)
    actions = {log.action for log in logs}
    assert "shop.activated" in actions
    assert "shop.deactivated" in actions


async def test_audit_staff_create(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Audit logs created for staff creation."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff1@example.com",
            "full_name": "Staff One",
            "password": "Password123!",
            "role": "staff",
        },
    )
    assert resp.status_code == 201
    membership_id = resp.json()["membership_id"]

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), action="staff.created", module="membership", shop_id=shop.id)
    assert len(logs) >= 1
    log = logs[0]
    assert log.action == "staff.created"
    assert log.module == "membership"
    assert log.entity_type == "shop_membership"
    assert log.entity_id == str(membership_id)
    assert log.new_values["role"] == "staff"
    assert log.new_values["email"] == "staff1@example.com"


async def test_audit_staff_update(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Audit logs created for staff update."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    # Create staff
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff1@example.com",
            "full_name": "Staff One",
            "password": "Password123!",
            "role": "staff",
        },
    )
    assert resp.status_code == 201
    membership_id = resp.json()["membership_id"]

    # Update staff
    resp = await client.patch(
        f"/api/v1/shops/{shop.id}/staff/{membership_id}",
        json={"full_name": "Updated Name"},
    )
    assert resp.status_code == 200

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), action="staff.updated", module="membership", shop_id=shop.id)
    assert len(logs) >= 1
    log = logs[0]
    assert log.action == "staff.updated"
    assert log.entity_type == "shop_membership"
    assert log.entity_id == str(membership_id)


async def test_audit_staff_role_change(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Audit logs created for staff role change."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    # Create staff
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff1@example.com",
            "full_name": "Staff One",
            "password": "Password123!",
            "role": "staff",
        },
    )
    assert resp.status_code == 201
    membership_id = resp.json()["membership_id"]

    # Change role
    resp = await client.patch(
        f"/api/v1/shops/{shop.id}/staff/{membership_id}/role",
        json={"role": "shop_manager"},
    )
    assert resp.status_code == 200

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), action="staff.role_changed", module="membership", shop_id=shop.id)
    assert len(logs) >= 1
    log = logs[0]
    assert log.action == "staff.role_changed"
    assert log.old_values["role"] == "staff"
    assert log.new_values["role"] == "shop_manager"


async def test_audit_staff_activate_deactivate(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Audit logs created for staff activate/deactivate."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    # Create staff
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff1@example.com",
            "full_name": "Staff One",
            "password": "Password123!",
            "role": "staff",
        },
    )
    assert resp.status_code == 201
    membership_id = resp.json()["membership_id"]

    # Deactivate
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff/{membership_id}/deactivate",
    )
    assert resp.status_code == 200

    # Activate
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff/{membership_id}/activate",
    )
    assert resp.status_code == 200

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), module="membership", shop_id=shop.id)
    actions = {log.action for log in logs}
    assert "staff.activated" in actions
    assert "staff.deactivated" in actions


async def test_audit_manager_assign_unassign(client: AsyncClient, login, create_user, create_shop) -> None:
    """Audit logs created for manager assign/unassign."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    manager = await create_user("manager@example.com", platform_role=PlatformRole.MANAGER)
    await login("owner@example.com")

    # Create shop
    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Manager Shop", "slug": "manager-shop"},
    )
    assert resp.status_code == 201
    shop_id = resp.json()["id"]

    # Assign manager
    resp = await client.post(
        f"/api/v1/platform/shops/{shop_id}/managers",
        json={"user_id": manager.id, "is_active": True},
    )
    assert resp.status_code == 201
    assignment_id = resp.json()["id"]

    # Unassign manager
    resp = await client.delete(
        f"/api/v1/platform/shops/{shop_id}/managers/{manager.id}",
    )
    assert resp.status_code == 204

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), module="shop", shop_id=shop_id)
    actions = {log.action for log in logs}
    assert "shop.manager_assigned" in actions
    assert "shop.manager_unassigned" in actions


async def test_audit_owner_change(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Audit logs created for owner change."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    new_owner = await create_user("newowner@example.com")
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await create_membership(new_owner, shop, ShopRole.STAFF)
    await login("owner@example.com")

    # Transfer ownership
    resp = await client.post(
        f"/api/v1/platform/shops/{shop.id}/owner",
        json={"new_owner_user_id": new_owner.id},
    )
    assert resp.status_code == 200

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), action="shop.owner_changed", module="shop", shop_id=shop.id)
    assert len(logs) >= 1
    log = logs[0]
    assert log.action == "shop.owner_changed"
    assert "primary_owner_id" in log.old_values
    assert "primary_owner_id" in log.new_values


async def test_audit_no_passwords_in_logs(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """No passwords/secrets stored in audit logs."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    # Create staff with password
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff1@example.com",
            "full_name": "Staff One",
            "password": "SecretPassword123!",
            "role": "staff",
        },
    )
    assert resp.status_code == 201

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), module="membership", shop_id=shop.id)

    # Check no log contains password or secret
    for log in logs:
        # Check old_values and new_values
        for field in ["old_values", "new_values", "extra"]:
            values = getattr(log, field, {}) or {}
            assert "password" not in str(values).lower()
            assert "secret" not in str(values).lower()
            assert "hashed_password" not in str(values).lower()


async def test_audit_login_failure_recorded(client: AsyncClient, create_user) -> None:
    """Failed login attempts are audited."""
    await create_user("alice@example.com", password="Password123!")

    # Failed login
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "WrongPassword"},
    )
    assert resp.status_code == 401

    # Fetch audit logs
    from app.core.database import get_session_factory
    logs = await get_audit_logs(get_session_factory(), action="login.failure", module="auth")
    assert len(logs) >= 1
    log = logs[0]
    assert log.action == "login.failure"
    assert log.module == "auth"
    # No sensitive data in failure log
    assert "password" not in str(log.new_values).lower() if log.new_values else True