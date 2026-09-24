#!/usr/bin/env python
"""Seed platform owner and sample shop for local development."""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_engine, get_session_factory
from app.core.security import hash_password
from app.models import Shop, ShopMembership, User
from app.core.roles import ShopRole, PlatformRole
from app.models.shop import ShopStatus


async def seed() -> None:
    """Create platform owner and sample shop."""
    engine = init_engine()
    factory = get_session_factory()

    async with factory() as session:
        # Check if platform owner already exists
        from sqlalchemy import select
        existing = await session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        if existing:
            print("Platform owner already exists, skipping seed.")
            return

        # Create platform owner
        owner = User(
            email="admin@example.com",
            full_name="Platform Admin",
            hashed_password=hash_password("Admin123!"),
            platform_role=PlatformRole.OWNER.value,
            is_active=True,
        )
        session.add(owner)
        await session.commit()
        await session.refresh(owner)
        print(f"Created platform owner: {owner.email} (id={owner.id})")

        # Create sample shop
        shop = Shop(
            code="SHOP-000001",
            name="Demo Shop",
            slug="demo-shop",
            status=ShopStatus.ACTIVE.value,
        )
        session.add(shop)
        await session.commit()
        await session.refresh(shop)
        print(f"Created shop: {shop.name} (id={shop.id}, code={shop.code})")

        # Create shop membership for platform owner as shop owner
        membership = ShopMembership(
            user_id=owner.id,
            shop_id=shop.id,
            role=ShopRole.OWNER.value,
            is_active=True,
        )
        session.add(membership)
        await session.commit()
        await session.refresh(membership)
        print(f"Created shop membership: user_id={owner.id}, shop_id={shop.id}, role=owner")

    print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())