"""Tests for Platform Shop Management (Phase 3)."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.roles import PlatformRole, ShopRole
from app.models import Shop, User
from app.models.shop import ShopStatus


async def test_platform_owner_can_create_shop_with_auto_code(client: AsyncClient, login, create_user) -> None:
    """Platform Owner/Admin can create shop with auto-generated code SHOP-XXXXXX."""
    # Create platform owner
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    await login("owner@example.com")

    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Test Shop", "slug": "test-shop"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"].startswith("SHOP-")
    assert data["name"] == "Test Shop"
    assert data["slug"] == "test-shop"
    assert data["status"] == "active"


async def test_platform_admin_can_create_shop(client: AsyncClient, login, create_user) -> None:
    """Platform Admin can create shop."""
    admin = await create_user("admin@example.com", platform_role=PlatformRole.ADMIN)
    await login("admin@example.com")

    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Admin Shop", "slug": "admin-shop"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"].startswith("SHOP-")


async def test_platform_manager_cannot_create_shop(client: AsyncClient, login, create_user) -> None:
    """Platform Manager cannot create shop."""
    manager = await create_user("manager@example.com", platform_role=PlatformRole.MANAGER)
    await login("manager@example.com")

    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Manager Shop", "slug": "manager-shop"},
    )
    assert resp.status_code == 403


async def test_platform_support_cannot_create_shop(client: AsyncClient, login, create_user) -> None:
    """Platform Support cannot create shop."""
    support = await create_user("support@example.com", platform_role=PlatformRole.SUPPORT)
    await login("support@example.com")

    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Support Shop", "slug": "support-shop"},
    )
    assert resp.status_code == 403


async def test_shop_staff_cannot_create_shop(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Shop staff cannot create shop."""
    user = await create_user("staff@example.com")
    shop = await create_shop("SHOP-001", "Staff Shop", "staff-shop")
    await create_membership(user, shop, ShopRole.STAFF)
    await login("staff@example.com")

    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "New Shop", "slug": "new-shop"},
    )
    assert resp.status_code == 403


async def test_shop_code_uniqueness(client: AsyncClient, login, create_user) -> None:
    """Shop code uniqueness is enforced."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    await login("owner@example.com")

    # Create first shop
    resp1 = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Shop 1", "slug": "shop-1"},
    )
    assert resp1.status_code == 201
    code1 = resp1.json()["code"]

    # Try to create another shop with manually specified same code (via direct DB not possible via API)
    # The API auto-generates codes, so test uniqueness at DB level
    # Second shop gets different code
    resp2 = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Shop 2", "slug": "shop-2"},
    )
    assert resp2.status_code == 201
    code2 = resp2.json()["code"]
    assert code1 != code2


async def test_shop_slug_normalization_and_uniqueness(client: AsyncClient, login, create_user) -> None:
    """Shop slug is normalized (lowercase, hyphens) and uniqueness enforced."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    await login("owner@example.com")

    # Create first shop with mixed case slug
    resp1 = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Shop 1", "slug": "My-Shop-1"},
    )
    assert resp1.status_code == 201
    slug1 = resp1.json()["slug"]
    assert slug1 == "my-shop-1"  # Normalized to lowercase

    # Try to create another with same normalized slug
    resp2 = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Shop 2", "slug": "MY-SHOP-1"},
    )
    assert resp2.status_code == 409  # Conflict
    error_detail = resp2.json().get("error", {}).get("message", "")
    assert "slug" in error_detail.lower()


async def test_activate_deactivate_shop_lifecycle(client: AsyncClient, login, create_user) -> None:
    """Activate / deactivate shop lifecycle."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    await login("owner@example.com")

    # Create shop
    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Lifecycle Shop", "slug": "lifecycle-shop"},
    )
    assert resp.status_code == 201
    shop_id = resp.json()["id"]

    # Deactivate
    resp = await client.post(
        f"/api/v1/platform/shops/{shop_id}/deactivate",
        json={"status": "inactive"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"

    # Activate
    resp = await client.post(
        f"/api/v1/platform/shops/{shop_id}/activate",
        json={},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # Suspend
    resp = await client.post(
        f"/api/v1/platform/shops/{shop_id}/deactivate",
        json={"status": "suspended"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"


async def test_inactive_shop_blocks_normal_operations(client: AsyncClient, login, create_user, create_shop, create_membership) -> None:
    """Inactive shop blocks normal shop operations for members (403 Forbidden)."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    await login("owner@example.com")

    # Create shop and deactivate it
    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Inactive Shop", "slug": "inactive-shop"},
    )
    assert resp.status_code == 201
    shop_id = resp.json()["id"]

    # Create a regular shop member
    member = await create_user("member@example.com")
    await client.post(
        f"/api/v1/platform/shops/{shop_id}/deactivate",
        json={"status": "inactive"},
    )

    # Login as member and try to access shop operations
    await login("member@example.com")
    resp = await client.get(f"/api/v1/shops/{shop_id}/memberships/me")
    assert resp.status_code == 403
    assert "inactive" in resp.json().get("error", {}).get("message", "").lower()


async def test_platform_manager_assignment(client: AsyncClient, login, create_user, create_shop) -> None:
    """Platform manager shop assignment tests."""
    owner = await create_user("owner@example.com", platform_role=PlatformRole.OWNER)
    admin = await create_user("admin@example.com", platform_role=PlatformRole.ADMIN)
    manager = await create_user("manager@example.com", platform_role=PlatformRole.MANAGER)

    # Create shop as owner
    await login("owner@example.com")
    resp = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Managed Shop", "slug": "managed-shop"},
    )
    assert resp.status_code == 201
    shop_id = resp.json()["id"]

    # Owner assigns manager to shop
    resp = await client.post(
        f"/api/v1/platform/shops/{shop_id}/managers",
        json={"user_id": manager.id, "is_active": True},
    )
    assert resp.status_code == 201
    assignment_id = resp.json()["id"]

    # Manager can access assigned shop
    await login("manager@example.com")
    resp = await client.get(f"/api/v1/platform/shops/{shop_id}")
    assert resp.status_code == 200

    # Manager cannot access unassigned shop
    await login("owner@example.com")
    resp2 = await client.post(
        "/api/v1/platform/shops",
        json={"name": "Other Shop", "slug": "other-shop"},
    )
    other_shop_id = resp2.json()["id"]

    await login("manager@example.com")
    resp = await client.get(f"/api/v1/platform/shops/{other_shop_id}")
    assert resp.status_code == 403

    # Duplicate manager assignment rejected
    await login("owner@example.com")
    resp = await client.post(
        f"/api/v1/platform/shops/{shop_id}/managers",
        json={"user_id": manager.id, "is_active": True},
    )
    assert resp.status_code == 409

    # Unassign manager
    resp = await client.delete(
        f"/api/v1/platform/shops/{shop_id}/managers/{manager.id}",
    )
    assert resp.status_code == 204

    # Manager can no longer access
    await login("manager@example.com")
    resp = await client.get(f"/api/v1/platform/shops/{shop_id}")
    assert resp.status_code == 403