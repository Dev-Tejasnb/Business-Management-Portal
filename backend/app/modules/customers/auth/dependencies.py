"""Customer authentication dependencies.

Provides reusable dependencies for customer authentication and tenant context.
"""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.core.session import RedisSessionStore, SessionStore
from app.core.database import get_db_session
from app.models.customer import Customer
from app.models.customer_account import CustomerAccount
from app.models.shop import Shop, ShopStatus


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------
def get_customer_session_store() -> SessionStore:
    """Provide the Redis-backed session store for customer sessions (override in tests)."""
    return RedisSessionStore(get_redis())


# ---------------------------------------------------------------------------
# Refresh-token cookie helpers
# ---------------------------------------------------------------------------
def _customer_cookie_options(*, max_age: int | None) -> dict:
    settings = get_settings()
    return {
        "key": settings.AUTH_COOKIE_NAME,  # Reuse the same cookie name
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": "/",
        "max_age": max_age,
        "domain": settings.AUTH_COOKIE_DOMAIN or None,
    }


def set_customer_refresh_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(value=token, **_customer_cookie_options(max_age=max_age))


def clear_customer_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )


def get_customer_refresh_token(request: Request) -> str | None:
    settings = get_settings()
    return request.cookies.get(settings.AUTH_COOKIE_NAME)


# ---------------------------------------------------------------------------
# Current customer account
# ---------------------------------------------------------------------------
async def get_current_customer(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerAccount:
    """Validate the bearer access token and resolve the active customer account."""
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
        customer_account_id = int(subject)
    except (TypeError, ValueError):
        raise UnauthorizedError() from None

    customer_account = await db.scalar(
        select(CustomerAccount).where(CustomerAccount.id == customer_account_id)
    )
    if customer_account is None or customer_account.status != "active":
        raise UnauthorizedError()
    return customer_account


# ---------------------------------------------------------------------------
# Customer tenant context (shop from the customer account)
# ---------------------------------------------------------------------------
async def get_customer_shop(
    shop_id: int,
    customer_account: Annotated[CustomerAccount, Depends(get_current_customer)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Shop:
    """Resolve the shop from the customer account, ensuring tenant isolation.

    The shop_id comes from the route path. We verify it matches the customer's shop.
    """
    if customer_account.shop_id != shop_id:
        raise ForbiddenError("Customer does not belong to this shop.", detail={"shop_id": shop_id})

    shop = await db.scalar(select(Shop).where(Shop.id == shop_id))
    if shop is None:
        raise ForbiddenError("Shop not found.", detail={"shop_id": shop_id})

    if shop.status != ShopStatus.ACTIVE.value:
        raise ForbiddenError(
            "Shop is inactive or suspended.",
            detail={"shop_id": shop_id, "shop_status": shop.status},
        )
    return shop


async def get_customer(
    customer_id: int,
    customer_account: Annotated[CustomerAccount, Depends(get_current_customer)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Customer:
    """Resolve the customer record, ensuring ownership.

    The customer_id comes from the route path. We verify it matches the customer account.
    """
    if customer_account.customer_id != customer_id:
        raise ForbiddenError("Customer does not match authenticated account.", detail={"customer_id": customer_id})

    customer = await db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.shop_id == customer_account.shop_id,
        )
    )
    if customer is None:
        raise ForbiddenError("Customer not found.", detail={"customer_id": customer_id})
    return customer