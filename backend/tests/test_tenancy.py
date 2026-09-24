"""Tests for tenant isolation and RBAC."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.roles import PlatformRole, ShopRole


# ---------------------------------------------------------------------------
# Cross-shop isolation
# ---------------------------------------------------------------------------
async def test_shop_user_cannot_access_other_shop(
    client: AsyncClient,
    create_user,
    create_shop,
    create_membership,
    login,
) -> None:
    user_a = await create_user("a@example.com", platform_role=None)
    user_b = await create_user("b@example.com", platform_role=None)
    shop_a = await create_shop("SHOPA", "Shop A", "shop-a")
    shop_b = await create_shop("SHOPB", "Shop B", "shop-b")
    await create_membership(user_a, shop_a, ShopRole.OWNER)
    await create_membership(user_b, shop_b, ShopRole.OWNER)

    # User A can access their own shop.
    await login("a@example.com")
    ok = await client.get(f"/api/v1/shops/{shop_a.id}/memberships/me")
    assert ok.status_code == 200
    assert ok.json()["shop_id"] == shop_a.id

    # User A must NOT access Shop B.
    denied = await client.get(f"/api/v1/shops/{shop_b.id}/memberships/me")
    assert denied.status_code == 403


async def test_unknown_shop_id_rejected(
    client: AsyncClient, create_user, create_shop, create_membership, login
) -> None:
    user = await create_user("a@example.com")
    shop = await create_shop("SHOPA", "Shop A", "shop-a")
    await create_membership(user, shop, ShopRole.OWNER)
    await login("a@example.com")
    resp = await client.get("/api/v1/shops/999999/memberships/me")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Platform role authorization
# ---------------------------------------------------------------------------
async def test_platform_role_required_to_create_shop(
    client: AsyncClient, create_user, login
) -> None:
    await create_user("manager@example.com", platform_role=PlatformRole.MANAGER)
    await login("manager@example.com")
    resp = await client.post(
        "/api/v1/shops",
        json={"code": "SHOPX", "name": "Shop X", "slug": "shop-x"},
    )
    assert resp.status_code == 403


async def test_platform_admin_can_create_shop(
    client: AsyncClient, create_user, login
) -> None:
    await create_user("admin@example.com", platform_role=PlatformRole.ADMIN)
    await login("admin@example.com")
    resp = await client.post(
        "/api/v1/shops",
        json={"code": "SHOPX", "name": "Shop X", "slug": "shop-x"},
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "shop-x"


async def test_platform_admin_can_view_shop_without_membership(
    client: AsyncClient, create_user, create_shop, login
) -> None:
    shop = await create_shop("SHOPA", "Shop A", "shop-a")
    await create_user("admin@example.com", platform_role=PlatformRole.ADMIN)
    await login("admin@example.com")
    resp = await client.get(f"/api/v1/shops/{shop.id}")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Shop role authorization
# ---------------------------------------------------------------------------
async def test_shop_owner_can_add_members(
    client: AsyncClient, create_user, create_shop, create_membership, login
) -> None:
    owner = await create_user("owner@example.com")
    new_member = await create_user("member@example.com")
    shop = await create_shop("SHOPA", "Shop A", "shop-a")
    await create_membership(owner, shop, ShopRole.OWNER)

    await login("owner@example.com")
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/memberships",
        json={"user_id": new_member.id, "role": ShopRole.STAFF.value},
    )
    assert resp.status_code == 201


async def test_shop_staff_cannot_add_members(
    client: AsyncClient, create_user, create_shop, create_membership, login
) -> None:
    staff = await create_user("staff@example.com")
    other = await create_user("other@example.com")
    shop = await create_shop("SHOPA", "Shop A", "shop-a")
    await create_membership(staff, shop, ShopRole.STAFF)

    await login("staff@example.com")
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/memberships",
        json={"user_id": other.id, "role": ShopRole.STAFF.value},
    )
    assert resp.status_code == 403


async def test_duplicate_membership_rejected(
    client: AsyncClient, create_user, create_shop, create_membership, login
) -> None:
    owner = await create_user("owner@example.com")
    member = await create_user("member@example.com")
    shop = await create_shop("SHOPA", "Shop A", "shop-a")
    await create_membership(owner, shop, ShopRole.OWNER)
    await create_membership(member, shop, ShopRole.STAFF)

    await login("owner@example.com")
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/memberships",
        json={"user_id": member.id, "role": ShopRole.MANAGER.value},
    )
    assert resp.status_code == 409