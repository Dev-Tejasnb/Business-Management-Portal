"""Shops/tenant business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.roles import ShopRole
from app.models.membership import ShopMembership
from app.models.shop import Shop, ShopStatus
from app.models.user import User


async def create_shop(db: AsyncSession, *, code: str, name: str, slug: str) -> Shop:
    """Create a new active shop, enforcing unique code and slug."""
    for field, value in (("code", code), ("slug", slug)):
        existing = await db.scalar(select(Shop).where(getattr(Shop, field) == value))
        if existing is not None:
            raise ConflictError(f"Shop {field} '{value}' is already in use.")
    shop = Shop(code=code, name=name, slug=slug, status=ShopStatus.ACTIVE.value)
    db.add(shop)
    await db.flush()
    return shop


async def list_shops(db: AsyncSession) -> list[Shop]:
    return list((await db.scalars(select(Shop).order_by(Shop.id))).all())


async def get_shop(db: AsyncSession, shop_id: int) -> Shop:
    shop = await db.scalar(select(Shop).where(Shop.id == shop_id))
    if shop is None:
        raise NotFoundError("Shop not found.")
    return shop


async def create_membership(
    db: AsyncSession, *, shop: Shop, user: User, role: ShopRole
) -> ShopMembership:
    """Add an active membership for a user in a shop (no duplicates)."""
    existing = await db.scalar(
        select(ShopMembership).where(
            ShopMembership.shop_id == shop.id, ShopMembership.user_id == user.id
        )
    )
    if existing is not None:
        raise ConflictError("User is already a member of this shop.")
    membership = ShopMembership(
        user_id=user.id, shop_id=shop.id, role=role.value, is_active=True
    )
    db.add(membership)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("User is already a member of this shop.") from None
    return membership


async def list_memberships(db: AsyncSession, shop_id: int) -> list[ShopMembership]:
    return list(
        (
            await db.scalars(
                select(ShopMembership)
                .where(ShopMembership.shop_id == shop_id)
                .order_by(ShopMembership.id)
            )
        ).all()
    )


async def get_user_by_id(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise NotFoundError("User not found.")
    return user