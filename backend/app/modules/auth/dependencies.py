"""Reusable authentication, tenant-context and RBAC dependencies.

This module centralizes how the authenticated user, the active shop membership,
and permission/role checks are resolved. Route handlers must rely on these
dependencies and must NOT trust user ids or shop ids supplied by the frontend.
"""

from __future__ import annotations

from typing import Annotated, Callable

import jwt
from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis import get_redis
from app.core.roles import (
    PlatformRole,
    ShopRole,
    SHOP_VIEW,
    platform_permissions_for,
    shop_permissions_for,
)
from app.core.security import decode_access_token
from app.core.session import RedisSessionStore, SessionStore
from app.core.tenant import TenantContext, build_tenant_context
from app.core.database import get_db_session
from app.models.manager_assignment import PlatformManagerShop
from app.models.membership import ShopMembership
from app.models.shop import Shop, ShopStatus
from app.models.user import User

# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------
def get_session_store() -> SessionStore:
    """Provide the Redis-backed session store (override in tests)."""
    return RedisSessionStore(get_redis())


# ---------------------------------------------------------------------------
# Refresh-token cookie helpers
# ---------------------------------------------------------------------------
def _cookie_options(*, max_age: int | None) -> dict:
    settings = get_settings()
    return {
        "key": settings.AUTH_COOKIE_NAME,
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": "/",
        "max_age": max_age,
        "domain": settings.AUTH_COOKIE_DOMAIN or None,
    }


def set_refresh_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(value=token, **_cookie_options(max_age=max_age))


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )


def get_refresh_token(request: Request) -> str | None:
    settings = get_settings()
    return request.cookies.get(settings.AUTH_COOKIE_NAME)


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Validate the bearer access token and resolve the active user."""
    header = request.headers.get("authorization")
    if not header or not header.lower().startswith("bearer "):
        raise UnauthorizedError()
    token = header.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise UnauthorizedError() from None

    subject = payload.get("sub")
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise UnauthorizedError() from None

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return user


# ---------------------------------------------------------------------------
# Shop membership / tenant context
# ---------------------------------------------------------------------------
async def get_current_membership(
    shop_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ShopMembership:
    """Resolve the caller's ACTIVE membership in ``shop_id`` (from the path).

    This is the central tenant gate: access is granted only when the
    authenticated user has an active membership in that shop. The ``shop_id``
    comes from the route path, never from a request body.

    Additionally enforces:
    - Shop must be active (unless caller is platform user with SHOP_VIEW permission)
    - Platform Managers must have an active assignment to the shop
    """
    # First, load the shop to check its status
    shop = await db.scalar(select(Shop).where(Shop.id == shop_id))
    if shop is None:
        raise ForbiddenError("Shop not found.", detail={"shop_id": shop_id})

    # Check if user is a platform user with SHOP_VIEW permission (bypasses shop status check)
    platform_perms = platform_permissions_for(user.platform_role_enum)
    is_platform_user_with_shop_view = SHOP_VIEW in platform_perms

    # If shop is not active and user doesn't have platform SHOP_VIEW permission, reject
    if shop.status != ShopStatus.ACTIVE.value and not is_platform_user_with_shop_view:
        raise ForbiddenError(
            "Shop is inactive or suspended.",
            detail={"shop_id": shop_id, "shop_status": shop.status},
        )

    # For Platform Managers, verify they have an active assignment to this shop
    if user.platform_role_enum == PlatformRole.MANAGER:
        assignment = await db.scalar(
            select(PlatformManagerShop).where(
                PlatformManagerShop.user_id == user.id,
                PlatformManagerShop.shop_id == shop_id,
                PlatformManagerShop.is_active.is_(True),
            )
        )
        if assignment is None:
            raise ForbiddenError(
                "You are not assigned to manage this shop.",
                detail={"shop_id": shop_id},
            )

    # Now resolve the shop membership
    membership = await db.scalar(
        select(ShopMembership).where(
            ShopMembership.user_id == user.id,
            ShopMembership.shop_id == shop_id,
            ShopMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise ForbiddenError(
            "You do not have access to this shop.",
            detail={"shop_id": shop_id},
        )
    return membership


def get_tenant_context(
    membership: Annotated[ShopMembership, Depends(get_current_membership)],
) -> TenantContext:
    """Build the immutable tenant context from a verified membership."""
    return build_tenant_context(shop_id=membership.shop_id, shop_role=membership.role)


# ---------------------------------------------------------------------------
# RBAC dependencies
# ---------------------------------------------------------------------------
def require_platform_role(*roles: PlatformRole) -> Callable:
    """Dependency factory: require the user to hold one of the platform roles."""

    async def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.platform_role_enum not in roles:
            raise ForbiddenError("You do not have the required platform role.")
        return user

    return _dep


def require_platform_permission(*perms: str) -> Callable:
    """Dependency factory: require a platform-scope permission (no membership)."""

    async def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not set(perms) & platform_permissions_for(user.platform_role_enum):
            raise ForbiddenError("You do not have the required platform permission.")
        return user

    return _dep


def require_shop_role(*roles: ShopRole) -> Callable:
    """Dependency factory: require an active membership with one of the shop roles."""

    async def _dep(
        membership: Annotated[ShopMembership, Depends(get_current_membership)],
    ) -> ShopMembership:
        if membership.role_enum not in roles:
            raise ForbiddenError("You do not have the required shop role.")
        return membership

    return _dep


def require_shop_permission(*perms: str) -> Callable:
    """Dependency factory: require a permission as an active shop member.

    Checks the membership's shop-role permissions (plus any platform permissions
    the user holds). The membership is resolved against the ``shop_id`` in the
    route path.
    """

    async def _dep(
        membership: Annotated[ShopMembership, Depends(get_current_membership)],
        user: Annotated[User, Depends(get_current_user)],
    ) -> ShopMembership:
        effective = shop_permissions_for(membership.role_enum)
        effective |= platform_permissions_for(user.platform_role_enum)
        if not set(perms) & effective:
            raise ForbiddenError("You do not have permission for this action.")
        return membership

    return _dep


async def _load_membership(
    db: AsyncSession, user_id: int, shop_id: int, user: User | None = None
) -> ShopMembership | None:
    """Load membership with optional shop status and manager assignment checks.

    If user is provided, enforces:
    - Shop must be active (unless caller is platform user with SHOP_VIEW permission)
    - Platform Managers must have an active assignment to the shop
    """
    # Check shop status if user provided
    if user is not None:
        shop = await db.scalar(select(Shop).where(Shop.id == shop_id))
        if shop is None:
            return None

        platform_perms = platform_permissions_for(user.platform_role_enum)
        is_platform_user_with_shop_view = SHOP_VIEW in platform_perms

        if shop.status != ShopStatus.ACTIVE.value and not is_platform_user_with_shop_view:
            return None

        if user.platform_role_enum == PlatformRole.MANAGER:
            assignment = await db.scalar(
                select(PlatformManagerShop).where(
                    PlatformManagerShop.user_id == user.id,
                    PlatformManagerShop.shop_id == shop_id,
                    PlatformManagerShop.is_active.is_(True),
                )
            )
            if assignment is None:
                return None

    return await db.scalar(
        select(ShopMembership).where(
            ShopMembership.user_id == user_id,
            ShopMembership.shop_id == shop_id,
            ShopMembership.is_active.is_(True),
        )
    )


def require_permission(*perms: str) -> Callable:
    """Dependency factory for a shop resource: platform OR shop access.

    Grants access if the user holds the permission via their platform role, or
    via an active shop membership. Returns the membership when shop access was
    used, otherwise None (pure platform access).

    Also enforces shop status and manager assignment checks for platform access.
    """

    async def _dep(
        shop_id: int,
        user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> ShopMembership | None:
        # Check if user has platform permission
        if set(perms) & platform_permissions_for(user.platform_role_enum):
            # Still need to verify shop status and manager assignment for platform users
            shop = await db.scalar(select(Shop).where(Shop.id == shop_id))
            if shop is None:
                raise ForbiddenError("Shop not found.", detail={"shop_id": shop_id})

            platform_perms = platform_permissions_for(user.platform_role_enum)
            is_platform_user_with_shop_view = SHOP_VIEW in platform_perms

            if shop.status != ShopStatus.ACTIVE.value and not is_platform_user_with_shop_view:
                raise ForbiddenError(
                    "Shop is inactive or suspended.",
                    detail={"shop_id": shop_id, "shop_status": shop.status},
                )

            if user.platform_role_enum == PlatformRole.MANAGER:
                assignment = await db.scalar(
                    select(PlatformManagerShop).where(
                        PlatformManagerShop.user_id == user.id,
                        PlatformManagerShop.shop_id == shop_id,
                        PlatformManagerShop.is_active.is_(True),
                    )
                )
                if assignment is None:
                    raise ForbiddenError(
                        "You are not assigned to manage this shop.",
                        detail={"shop_id": shop_id},
                    )
            return None

        # Shop membership path
        membership = await _load_membership(db, user.id, shop_id, user)
        if membership is None:
            raise ForbiddenError(
                "You do not have access to this shop.",
                detail={"shop_id": shop_id},
            )
        if set(perms) & shop_permissions_for(membership.role_enum):
            return membership
        raise ForbiddenError("You do not have permission for this action.")

    return _dep