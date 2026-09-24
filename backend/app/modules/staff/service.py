"""Staff management business logic and database queries."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.roles import ShopRole
from app.modules.staff.schemas import AssignableStaffRole
from app.core.security import hash_password
from app.models.membership import ShopMembership
from app.models.shop import Shop, ShopStatus
from app.models.user import User


async def count_active_owners(db: AsyncSession, shop_id: int) -> int:
    """Count active shop owners in a shop."""
    return await db.scalar(
        select(func.count(ShopMembership.id)).where(
            ShopMembership.shop_id == shop_id,
            ShopMembership.role == ShopRole.OWNER.value,
            ShopMembership.is_active.is_(True),
        )
    ) or 0


async def create_staff(
    db: AsyncSession,
    *,
    shop_id: int,
    email: str,
    full_name: str,
    password: str,
    role: AssignableStaffRole | ShopRole,
) -> tuple[User, ShopMembership]:
    """Create a new user (if not exists) and membership for a shop.

    Creates User with Argon2id hashed password and ShopMembership.
    SHOP_OWNER cannot be assigned via this function (must use owner transfer).
    """
    # Defensive check: ensure SHOP_OWNER cannot be assigned through staff creation
    role_val = role.value if hasattr(role, 'value') else str(role)
    if role_val == ShopRole.OWNER.value:
        raise ValidationError("Cannot assign SHOP_OWNER role via staff creation. Use owner transfer instead.")

    # Check if user exists
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        # Create new user
        hashed = hash_password(password)
        user = User(
            email=email.lower(),
            full_name=full_name.strip(),
            hashed_password=hashed,
            is_active=True,
        )
        db.add(user)
        await db.flush()

    # Check if membership already exists
    existing = await db.scalar(
        select(ShopMembership).where(
            ShopMembership.shop_id == shop_id,
            ShopMembership.user_id == user.id,
        )
    )
    if existing is not None:
        if existing.is_active:
            raise ConflictError("User is already an active member of this shop.")
        # Reactivate if inactive
        existing.role = role_val
        existing.is_active = True
        await db.flush()
        return user, existing

    # Create membership
    membership = ShopMembership(
        shop_id=shop_id,
        user_id=user.id,
        role=role_val,
        is_active=True,
    )
    db.add(membership)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("User is already a member of this shop.") from None

    return user, membership


async def list_staff(
    db: AsyncSession,
    shop_id: int,
    *,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ShopMembership], int]:
    """List staff memberships for a shop with filters and pagination."""
    query = (
        select(ShopMembership)
        .options(selectinload(ShopMembership.user))
        .where(ShopMembership.shop_id == shop_id)
    )

    if search:
        term = f"%{search.strip()}%"
        query = query.join(User).where(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )

    if role:
        query = query.where(ShopMembership.role == role)

    if is_active is not None:
        query = query.where(ShopMembership.is_active.is_(is_active))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination and sorting
    query = query.order_by(ShopMembership.id.desc()).offset((page - 1) * page_size).limit(page_size)
    memberships = list((await db.scalars(query)).all())

    return memberships, total


async def get_staff_membership(db: AsyncSession, shop_id: int, membership_id: int) -> ShopMembership:
    """Get a staff membership by ID within a shop."""
    membership = await db.scalar(
        select(ShopMembership)
        .options(selectinload(ShopMembership.user))
        .where(
            ShopMembership.id == membership_id,
            ShopMembership.shop_id == shop_id,
        )
    )
    if membership is None:
        raise NotFoundError("Staff membership not found.")
    return membership


async def update_staff_profile(
    db: AsyncSession,
    shop_id: int,
    membership_id: int,
    *,
    full_name: Optional[str] = None,
) -> ShopMembership:
    """Update staff profile (full_name)."""
    membership = await get_staff_membership(db, shop_id, membership_id)

    if full_name is not None:
        membership.user.full_name = full_name.strip()
        await db.flush()

    return membership


async def change_staff_role(
    db: AsyncSession,
    shop_id: int,
    membership_id: int,
    new_role: ShopRole,
) -> ShopMembership:
    """Change a staff member's role.

    Enforces that the shop cannot lose its only owner.
    """
    membership = await get_staff_membership(db, shop_id, membership_id)
    old_role = membership.role

    # If demoting from owner, check there will be at least one other active owner
    if old_role == ShopRole.OWNER.value and new_role != ShopRole.OWNER:
        active_owners = await count_active_owners(db, shop_id)
        if active_owners <= 1:
            raise ForbiddenError(
                "Cannot demote the only active shop owner. Transfer ownership first.",
                detail={"shop_id": shop_id},
            )

    membership.role = new_role.value
    await db.flush()
    await db.refresh(membership)
    return membership


async def activate_staff(db: AsyncSession, shop_id: int, membership_id: int) -> ShopMembership:
    """Activate a staff membership (set is_active=True)."""
    membership = await get_staff_membership(db, shop_id, membership_id)
    if membership.is_active:
        raise ValidationError("Staff membership is already active.")
    membership.is_active = True
    await db.flush()
    await db.refresh(membership)
    return membership


async def deactivate_staff(db: AsyncSession, shop_id: int, membership_id: int) -> ShopMembership:
    """Deactivate a staff membership (set is_active=False).

    Preserves the User account. Prevents deactivating the only shop owner.
    """
    membership = await get_staff_membership(db, shop_id, membership_id)
    if not membership.is_active:
        raise ValidationError("Staff membership is already inactive.")

    # Prevent deactivating the only active owner
    if membership.role == ShopRole.OWNER.value:
        active_owners = await count_active_owners(db, shop_id)
        if active_owners <= 1:
            raise ForbiddenError(
                "Cannot deactivate the only active shop owner. Transfer ownership first.",
                detail={"shop_id": shop_id},
            )

    membership.is_active = False
    await db.flush()
    await db.refresh(membership)
    return membership


async def delete_staff_membership(db: AsyncSession, shop_id: int, membership_id: int) -> None:
    """Remove a staff membership entirely.

    Does NOT delete the User account. Prevents removing the only shop owner.
    """
    membership = await get_staff_membership(db, shop_id, membership_id)

    # Prevent removing the only active owner
    if membership.role == ShopRole.OWNER.value and membership.is_active:
        active_owners = await count_active_owners(db, shop_id)
        if active_owners <= 1:
            raise ForbiddenError(
                "Cannot remove the only active shop owner. Transfer ownership first.",
                detail={"shop_id": shop_id},
            )

    await db.delete(membership)
    await db.flush()