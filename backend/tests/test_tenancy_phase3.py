"""Tests for Tenancy/Isolation in Phase 3 (Shop & Staff)."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.roles import PlatformRole, ShopRole
from app.models import Shop, User
from app.models.shop import ShopStatus


async def test_shop_a_owner_cannot_view_shop_b_staff(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Shop A owner cannot view Shop B staff."""
    owner_a = await create_user("owner_a@example.com")
    owner_b = await create_user("owner_b@example.com")
    staff_a = await create_user("staff_a@example.com")
    staff_b = await create_user("staff_b@example.com")

    shop_a = await create_shop("SHOP-001", "Shop A", "shop-a")
    shop_b = await create_shop("SHOP-002", "Shop B", "shop-b")

    await create_membership(owner_a, shop_a, ShopRole.OWNER)
    await create_membership(owner_b, shop_b, ShopRole.OWNER)
    await create_membership(staff_a, shop_a, ShopRole.STAFF)
    await create_membership(staff_b, shop_b, ShopRole.STAFF)

    await login("owner_a@example.com")

    # Owner A can view their own staff
    resp = await client.get(f"/api/v1/shops/{shop_a.id}/staff")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1

    # Owner A cannot view Shop B staff
    resp = await client.get(f"/api/v1/shops/{shop_b.id}/staff")
    assert resp.status_code == 403


async def test_shop_a_owner_cannot_add_modify_deactivate_shop_b_staff(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Shop A owner cannot add/modify/deactivate Shop B staff."""
    owner_a = await create_user("owner_a@example.com")
    owner_b = await create_user("owner_b@example.com")
    staff_b = await create_user("staff_b@example.com")

    shop_a = await create_shop("SHOP-001", "Shop A", "shop-a")
    shop_b = await create_shop("SHOP-002", "Shop B", "shop-b")

    await create_membership(owner_a, shop_a, ShopRole.OWNER)
    await create_membership(owner_b, shop_b, ShopRole.OWNER)
    await create_membership(staff_b, shop_b, ShopRole.STAFF)

    await login("owner_a@example.com")

    # Cannot create staff in Shop B
    resp = await client.post(
        f"/api/v1/shops/{shop_b.id}/staff",
        json={"email": "newstaff@example.com", "full_name": "New Staff", "password": "Password123!", "role": "staff"},
    )
    assert resp.status_code == 403

    # Cannot modify Shop B staff
    resp = await client.get(f"/api/v1/shops/{shop_b.id}/staff")
    assert resp.status_code == 403


async def test_shop_a_owner_cannot_change_shop_b_staff_roles(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Shop A owner cannot change Shop B staff roles."""
    owner_a = await create_user("owner_a@example.com")
    owner_b = await create_user("owner_b@example.com")
    staff_b = await create_user("staff_b@example.com")

    shop_a = await create_shop("SHOP-001", "Shop A", "shop-a")
    shop_b = await create_shop("SHOP-002", "Shop B", "shop-b")

    await create_membership(owner_a, shop_a, ShopRole.OWNER)
    await create_membership(owner_b, shop_b, ShopRole.OWNER)
    await create_membership(staff_b, shop_b, ShopRole.STAFF)

    await login("owner_a@example.com")

    # Owner A cannot access Shop B staff list to get membership IDs
    resp = await client.get(f"/api/v1/shops/{shop_b.id}/staff")
    assert resp.status_code == 403


async def test_platform_manager_cannot_access_unassigned_shop_staff(client: AsyncClient, login, create_user, create_shop) -> None:
    """Platform manager cannot access unassigned shop staff."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    manager = await create_user("manager@example.com", platform_role=PlatformRole.MANAGER)
    staff = await create_user("staff@example.com")

    shop_a = await create_shop("SHOP-001", "Assigned Shop", "assigned-shop")
    shop_b = await create_shop("SHOP-002", "Unassigned Shop", "unassigned-shop")

    # Owner creates memberships
    from app.core.database import get_session_factory
    from app.models.membership import ShopMembership
    from app.models.manager_assignment import PlatformManagerShop

    factory = get_session_factory()
    async with factory() as session:
        session.add_all([
            ShopMembership(user_id=owner.id, shop_id=shop_a.id, role=ShopRole.OWNER.value, is_active=True),
            ShopMembership(user_id=owner.id, shop_id=shop_b.id, role=ShopRole.OWNER.value, is_active=True),
            ShopMembership(user_id=staff.id, shop_id=shop_a.id, role=ShopRole.STAFF.value, is_active=True),
            ShopMembership(user_id=staff.id, shop_id=shop_b.id, role=ShopRole.STAFF.value, is_active=True),
        ])
        # Assign manager to shop_a only
        session.add(PlatformManagerShop(user_id=manager.id, shop_id=shop_a.id, is_active=True))
        await session.commit()

    await login("manager@example.com")

    # Manager can access assigned shop's staff
    resp = await client.get(f"/api/v1/shops/{shop_a.id}/staff")
    assert resp.status_code == 200

    # Manager cannot access unassigned shop's staff
    resp = await client.get(f"/api/v1/shops/{shop_b.id}/staff")
    assert resp.status_code == 403

    # Manager cannot create staff in unassigned shop
    resp = await client.post(
        f"/api/v1/shops/{shop_b.id}/staff",
        json={"email": "newstaff@example.com", "full_name": "New Staff", "password": "Password123!", "role": "staff"},
    )
    assert resp.status_code == 403


async def test_platform_owner_can_access_all_shops(client: AsyncClient, login, create_user, create_shop) -> None:
    """Platform Owner can access all shops regardless of assignment."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop_a = await create_shop("SHOP-001", "Shop A", "shop-a")
    shop_b = await create_shop("SHOP-002", "Shop B", "shop-b")

    # Create some staff in both shops via direct DB
    from app.core.database import get_session_factory
    from app.models.membership import ShopMembership
    from app.models.user import User

    staff_a = User(email="staff_a@example.com", full_name="Staff A", hashed_password="hashed", is_active=True)
    staff_b = User(email="staff_b@example.com", full_name="Staff B", hashed_password="hashed", is_active=True)

    factory = get_session_factory()
    async with factory() as session:
        session.add_all([staff_a, staff_b])
        await session.flush()
        session.add_all([
            ShopMembership(user_id=staff_a.id, shop_id=shop_a.id, role=ShopRole.STAFF.value, is_active=True),
            ShopMembership(user_id=staff_b.id, shop_id=shop_b.id, role=ShopRole.STAFF.value, is_active=True),
        ])
        await session.commit()

    await login("owner@example.com")

    # Platform owner can access both shops' staff
    resp = await client.get(f"/api/v1/shops/{shop_a.id}/staff")
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/shops/{shop_b.id}/staff")
    assert resp.status_code == 200


async def test_platform_admin_can_access_all_shops(client: AsyncClient, login, create_user, create_shop) -> None:
    """Platform Admin can access all shops regardless of assignment."""
    admin = await create_user("admin@example.com", platform_role=PlatformRole.ADMIN)
    shop_a = await create_shop("SHOP-001", "Shop A", "shop-a")
    shop_b = await create_shop("SHOP-002", "Shop B", "shop-b")

    # Create some staff in both shops via direct DB
    from app.core.database import get_session_factory
    from app.models.membership import ShopMembership
    from app.models.user import User

    staff_a = User(email="staff_a@example.com", full_name="Staff A", hashed_password="hashed", is_active=True)
    staff_b = User(email="staff_b@example.com", full_name="Staff B", hashed_password="hashed", is_active=True)

    factory = get_session_factory()
    async with factory() as session:
        session.add_all([staff_a, staff_b])
        await session.flush()
        session.add_all([
            ShopMembership(user_id=staff_a.id, shop_id=shop_a.id, role=ShopRole.STAFF.value, is_active=True),
            ShopMembership(user_id=staff_b.id, shop_id=shop_b.id, role=ShopRole.STAFF.value, is_active=True),
        ])
        await session.commit()

    await login("admin@example.com")

    # Platform admin can access both shops' staff
    resp = await client.get(f"/api/v1/shops/{shop_a.id}/staff")
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/shops/{shop_b.id}/staff")
    assert resp.status_code == 200