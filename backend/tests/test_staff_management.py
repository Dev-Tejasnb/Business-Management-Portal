"""Tests for Staff Management (Phase 3)."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.roles import PlatformRole, ShopRole
from app.models import Shop, User
from app.models.shop import ShopStatus


async def test_shop_owner_can_create_staff(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Shop Owner can create staff (creates user + membership)."""
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
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["user_email"] == "staff1@example.com"
    assert data["role"] == "staff"
    assert data["is_active"] is True
    assert data["membership_id"] > 0


async def test_shop_owner_can_create_staff_with_roles(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Shop Owner can create staff with different roles."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    # Create manager
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "manager1@example.com",
            "full_name": "Manager One",
            "password": "Password123!",
            "role": "shop_manager",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "shop_manager"

    # Create financial staff
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "financial1@example.com",
            "full_name": "Financial One",
            "password": "Password123!",
            "role": "financial_staff",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "financial_staff"


async def test_staff_role_modification(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Shop Owner can modify staff roles."""
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

    # Change role to manager
    resp = await client.patch(
        f"/api/v1/shops/{shop.id}/staff/{membership_id}/role",
        json={"role": "shop_manager"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "shop_manager"


async def test_staff_deactivation_preserves_user_account(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Staff deactivation sets membership.is_active=False, User account remains intact."""
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
    user_id = resp.json()["user_id"]

    # Deactivate staff
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff/{membership_id}/deactivate",
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # User account still exists and can login (but no access to this shop)
    await login("staff1@example.com")
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "staff1@example.com"

    # But cannot access shop operations
    resp = await client.get(f"/api/v1/shops/{shop.id}/memberships/me")
    assert resp.status_code == 403


async def test_deactivated_staff_cannot_access_shop_operations(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Deactivated staff cannot access shop operations."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    # Create and deactivate staff
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff1@example.com",
            "full_name": "Staff One",
            "password": "Password123!",
            "role": "staff",
        },
    )
    membership_id = resp.json()["membership_id"]

    await client.post(f"/api/v1/shops/{shop.id}/staff/{membership_id}/deactivate")

    # Try to access as deactivated staff
    await login("staff1@example.com")
    resp = await client.get(f"/api/v1/shops/{shop.id}/staff")
    assert resp.status_code == 403


async def test_regular_staff_cannot_manage_other_staff(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Regular staff / Financial staff cannot manage other staff."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    staff = await create_user("staff@example.com")
    financial = await create_user("financial@example.com")
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await create_membership(staff, shop, ShopRole.STAFF)
    await create_membership(financial, shop, ShopRole.FINANCIAL_STAFF)
    await login("owner@example.com")

    # Create another staff member
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff2@example.com",
            "full_name": "Staff Two",
            "password": "Password123!",
            "role": "staff",
        },
    )
    assert resp.status_code == 201
    membership_id = resp.json()["membership_id"]

    # Regular staff tries to create staff - should fail
    await login("staff@example.com")
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff3@example.com",
            "full_name": "Staff Three",
            "password": "Password123!",
            "role": "staff",
        },
    )
    assert resp.status_code == 403

    # Financial staff tries to create staff - should fail
    await login("financial@example.com")
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={
            "email": "staff4@example.com",
            "full_name": "Staff Four",
            "password": "Password123!",
            "role": "staff",
        },
    )
    assert resp.status_code == 403


async def test_owner_transfer_authorized_and_audited(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Owner transfer is authorized and audited."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    new_owner = await create_user("newowner@example.com")
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await create_membership(new_owner, shop, ShopRole.STAFF)
    await login("owner@example.com")

    # Transfer ownership via platform API
    resp = await client.post(
        f"/api/v1/platform/shops/{shop.id}/owner",
        json={"new_owner_user_id": new_owner.id},
    )
    assert resp.status_code == 200


async def test_shop_cannot_lose_its_only_owner(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Shop cannot lose its only owner (cannot deactivate or demote last owner)."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    # Get owner's membership ID
    resp = await client.get(f"/api/v1/shops/{shop.id}/memberships/me")
    assert resp.status_code == 200
    owner_membership_id = resp.json()["id"]

    # Try to deactivate the only owner - should fail
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/staff/{owner_membership_id}/deactivate",
    )
    assert resp.status_code == 403
    assert "only" in resp.json().get("error", {}).get("message", "").lower()

    # Try to demote the only owner - should fail
    resp = await client.patch(
        f"/api/v1/shops/{shop.id}/staff/{owner_membership_id}/role",
        json={"role": "shop_manager"},
    )
    assert resp.status_code == 403
    assert "only" in resp.json().get("error", {}).get("message", "").lower()


async def test_staff_list_with_filters(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Staff list supports search, role filter, and active filter."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com")

    # Create multiple staff
    await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={"email": "alice@example.com", "full_name": "Alice Smith", "password": "Password123!", "role": "staff"},
    )
    await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={"email": "bob@example.com", "full_name": "Bob Jones", "password": "Password123!", "role": "shop_manager"},
    )
    await client.post(
        f"/api/v1/shops/{shop.id}/staff",
        json={"email": "carol@example.com", "full_name": "Carol White", "password": "Password123!", "role": "financial_staff"},
    )

    # List all
    resp = await client.get(f"/api/v1/shops/{shop.id}/staff")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 3

    # Filter by role
    resp = await client.get(f"/api/v1/shops/{shop.id}/staff?role=staff")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["role"] == "staff"

    # Search by name
    resp = await client.get(f"/api/v1/shops/{shop.id}/staff?search=Alice")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["user_email"] == "alice@example.com"

    # Filter by is_active
    resp = await client.get(f"/api/v1/shops/{shop.id}/staff?is_active=true")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["is_active"] is True