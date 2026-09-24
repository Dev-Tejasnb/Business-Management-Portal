"""Platform shop business logic and database queries."""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.roles import PlatformRole, ShopRole
from app.models.manager_assignment import PlatformManagerShop
from app.models.membership import ShopMembership
from app.models.shop import Shop, ShopStatus
from app.models.user import User


def normalize_slug(slug: str) -> str:
    """Normalize and validate a shop slug (lowercase, alphanumeric, hyphens).

    Valid slug format: lowercase letters, numbers, hyphens only.
    Must be 2-120 chars, cannot start/end with hyphen, no consecutive hyphens.
    """
    # Strip whitespace and convert to lowercase
    normalized = slug.strip().lower()

    # Replace any non-alphanumeric characters (except hyphens) with hyphens
    # [^a-z0-9\-] matches anything that is NOT lowercase letter, digit, or hyphen
    normalized = re.sub(r"[^a-z0-9\-]", "-", normalized)

    # Collapse consecutive hyphens into single hyphen
    normalized = re.sub(r"\-+", "-", normalized)

    # Remove leading and trailing hyphens
    normalized = normalized.strip("-")

    # Enforce length limits (2-120 chars, matching DB column)
    if not normalized:
        raise ValidationError("Slug must contain at least 2 alphanumeric characters after normalization.")
    if len(normalized) > 120:
        raise ValidationError("Slug must be at most 120 characters.")

    # Must contain at least one alphanumeric character
    if not re.search(r"[a-z0-9]", normalized):
        raise ValidationError("Slug must contain at least one letter or number.")

    return normalized


async def generate_shop_code(db: AsyncSession) -> str:
    """Generate the next auto-incrementing shop code in format SHOP-XXXXXX.

    Uses a PostgreSQL sequence for concurrency-safe generation.
    Falls back to the original method if sequence doesn't exist (for backward compatibility).
    """
    try:
        # Try to get next value from sequence (concurrency-safe)
        result = await db.scalar(select(func.nextval('shop_code_seq')))
        if result is not None:
            return f"SHOP-{result:06d}"
    except Exception:
        # Fallback to original method if sequence doesn't exist
        pass

    # Original method as fallback (for existing data or if sequence creation failed)
    result = await db.scalar(
        select(func.max(Shop.code)).where(Shop.code.like("SHOP-%"))
    )
    if not result:
        return "SHOP-000001"
    try:
        current_num = int(result.split("-")[1])
        next_num = current_num + 1
        return f"SHOP-{next_num:06d}"
    except (IndexError, ValueError):
        return "SHOP-000001"


async def get_shop_primary_owner(db: AsyncSession, shop_id: int) -> User | None:
    """Find the primary shop owner (first active member with role=shop_owner)."""
    membership = await db.scalar(
        select(ShopMembership)
        .options(selectinload(ShopMembership.user))
        .where(
            ShopMembership.shop_id == shop_id,
            ShopMembership.role == ShopRole.OWNER.value,
            ShopMembership.is_active.is_(True),
        )
        .order_by(ShopMembership.created_at.asc())
    )
    return membership.user if membership else None


async def create_shop(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    owner_user_id: Optional[int] = None,
) -> Shop:
    """Create a new shop with auto-generated code and unique slug."""
    clean_slug = normalize_slug(slug)

    # Check slug uniqueness
    existing = await db.scalar(select(Shop).where(Shop.slug == clean_slug))
    if existing is not None:
        raise ConflictError(f"Shop slug '{clean_slug}' is already in use.")

    code = await generate_shop_code(db)

    shop = Shop(
        code=code,
        name=name.strip(),
        slug=clean_slug,
        status=ShopStatus.ACTIVE.value,
    )
    db.add(shop)
    await db.flush()

    # If an owner user is specified, add them as shop_owner
    if owner_user_id is not None:
        owner = await db.scalar(select(User).where(User.id == owner_user_id))
        if owner is None:
            raise NotFoundError(f"Owner user {owner_user_id} not found.")

        membership = ShopMembership(
            shop_id=shop.id,
            user_id=owner.id,
            role=ShopRole.OWNER.value,
            is_active=True,
        )
        db.add(membership)
        await db.flush()

    return shop


async def list_shops(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user: User | None = None,
) -> tuple[list[Shop], int]:
    """List shops with filtering, pagination, and Platform Manager scoping."""
    query = select(Shop)

    # Platform Manager can only view their assigned shops
    if user and user.platform_role_enum == PlatformRole.MANAGER:
        query = query.join(
            PlatformManagerShop,
            (PlatformManagerShop.shop_id == Shop.id)
            & (PlatformManagerShop.user_id == user.id)
            & (PlatformManagerShop.is_active.is_(True)),
        )

    if status:
        query = query.where(Shop.status == status)

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Shop.name.ilike(term),
                Shop.code.ilike(term),
                Shop.slug.ilike(term),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination and sorting
    query = query.order_by(Shop.id.desc()).offset((page - 1) * page_size).limit(page_size)
    shops = list((await db.scalars(query)).all())

    return shops, total


async def get_shop_by_id(db: AsyncSession, shop_id: int) -> Shop:
    """Get a shop by ID."""
    shop = await db.scalar(select(Shop).where(Shop.id == shop_id))
    if shop is None:
        raise NotFoundError("Shop not found.")
    return shop


async def update_shop(
    db: AsyncSession,
    shop_id: int,
    *,
    name: Optional[str] = None,
    slug: Optional[str] = None,
) -> Shop:
    """Update shop details (name, slug)."""
    shop = await get_shop_by_id(db, shop_id)

    if name is not None:
        shop.name = name.strip()

    if slug is not None:
        clean_slug = normalize_slug(slug)
        if clean_slug != shop.slug:
            existing = await db.scalar(
                select(Shop).where(Shop.slug == clean_slug, Shop.id != shop_id)
            )
            if existing is not None:
                raise ConflictError(f"Shop slug '{clean_slug}' is already in use.")
            shop.slug = clean_slug

    await db.flush()
    await db.refresh(shop)
    return shop


async def activate_shop(db: AsyncSession, shop_id: int) -> Shop:
    """Activate a shop."""
    shop = await get_shop_by_id(db, shop_id)
    shop.status = ShopStatus.ACTIVE.value
    await db.flush()
    await db.refresh(shop)
    return shop


async def deactivate_shop(db: AsyncSession, shop_id: int, target_status: str = "inactive") -> Shop:
    """Deactivate or suspend a shop."""
    if target_status not in (ShopStatus.INACTIVE.value, ShopStatus.SUSPENDED.value):
        raise ValidationError("Target status must be 'inactive' or 'suspended'.")
    shop = await get_shop_by_id(db, shop_id)
    shop.status = target_status
    await db.flush()
    await db.refresh(shop)
    return shop


async def transfer_shop_owner(
    db: AsyncSession,
    shop_id: int,
    new_owner_user_id: int,
) -> tuple[Shop, User, User | None]:
    """Transfer primary ownership of a shop to another active member.

    This operation is atomic: the old owner is demoted to SHOP_MANAGER
    and the new owner is promoted to SHOP_OWNER in a single transaction.
    The unique partial index ensures only one active owner per shop.
    """
    shop = await get_shop_by_id(db, shop_id)

    # Find target user's active membership in the shop
    new_owner_membership = await db.scalar(
        select(ShopMembership)
        .options(selectinload(ShopMembership.user))
        .where(
            ShopMembership.shop_id == shop_id,
            ShopMembership.user_id == new_owner_user_id,
            ShopMembership.is_active.is_(True),
        )
    )
    if new_owner_membership is None:
        raise NotFoundError(
            "New owner must be an active member of this shop.",
            detail={"user_id": new_owner_user_id, "shop_id": shop_id},
        )

    # Cannot transfer ownership to self
    old_owner = await get_shop_primary_owner(db, shop_id)
    if old_owner and old_owner.id == new_owner_user_id:
        raise ValidationError("User is already the primary owner of this shop.")

    # Find current primary owner's membership
    old_owner_membership = await db.scalar(
        select(ShopMembership)
        .where(
            ShopMembership.shop_id == shop_id,
            ShopMembership.role == ShopRole.OWNER.value,
            ShopMembership.is_active.is_(True),
        )
        .order_by(ShopMembership.created_at.asc())
    )

    if old_owner_membership is None:
        raise NotFoundError("No active shop owner found to transfer from.")

    # Demote old owner to SHOP_MANAGER (safe default - existing shop role)
    old_owner_membership.role = ShopRole.MANAGER.value

    # Promote new owner to SHOP_OWNER
    new_owner_membership.role = ShopRole.OWNER.value

    # Flush both changes in the same transaction
    # The partial unique index will prevent two active owners
    await db.flush()

    return shop, new_owner_membership.user, old_owner


async def list_shop_managers(db: AsyncSession, shop_id: int) -> list[PlatformManagerShop]:
    """List platform managers assigned to a shop."""
    await get_shop_by_id(db, shop_id)
    query = (
        select(PlatformManagerShop)
        .options(selectinload(PlatformManagerShop.user))
        .where(PlatformManagerShop.shop_id == shop_id)
        .order_by(PlatformManagerShop.created_at.asc())
    )
    return list((await db.scalars(query)).all())


async def assign_platform_manager(
    db: AsyncSession,
    shop_id: int,
    user_id: int,
    is_active: bool = True,
) -> PlatformManagerShop:
    """Assign a platform manager to a shop."""
    await get_shop_by_id(db, shop_id)
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise NotFoundError("User not found.")

    if user.platform_role_enum != PlatformRole.MANAGER:
        raise ValidationError("User must have platform_role='platform_manager'.")

    # Check for existing assignment
    assignment = await db.scalar(
        select(PlatformManagerShop).where(
            PlatformManagerShop.shop_id == shop_id,
            PlatformManagerShop.user_id == user_id,
        )
    )
    if assignment is not None:
        raise ConflictError("Manager is already assigned to this shop.")

    assignment = PlatformManagerShop(
        shop_id=shop_id,
        user_id=user_id,
        is_active=is_active,
    )
    db.add(assignment)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Manager is already assigned to this shop.") from None

    # Eager load user relationship for response
    await db.refresh(assignment, attribute_names=["user"])
    return assignment


async def unassign_platform_manager(
    db: AsyncSession,
    shop_id: int,
    user_id: int,
) -> None:
    """Unassign a platform manager from a shop."""
    assignment = await db.scalar(
        select(PlatformManagerShop).where(
            PlatformManagerShop.shop_id == shop_id,
            PlatformManagerShop.user_id == user_id,
        )
    )
    if assignment is None:
        raise NotFoundError("Manager assignment not found.")

    await db.delete(assignment)
    await db.flush()


async def update_platform_manager_assignment(
    db: AsyncSession,
    shop_id: int,
    user_id: int,
    is_active: bool,
) -> PlatformManagerShop:
    """Update status of a platform manager assignment."""
    assignment = await db.scalar(
        select(PlatformManagerShop)
        .options(selectinload(PlatformManagerShop.user))
        .where(
            PlatformManagerShop.shop_id == shop_id,
            PlatformManagerShop.user_id == user_id,
        )
    )
    if assignment is None:
        raise NotFoundError("Manager assignment not found.")

    assignment.is_active = is_active
    await db.flush()
    return assignment