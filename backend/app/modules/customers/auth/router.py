"""Customer Authentication API endpoints under /api/v1/customer-auth.

Implements login, refresh (cookie-based rotation), logout and current-customer.
Refresh tokens are delivered as HTTP-only cookies; access tokens are returned in
the response body and are held in memory by the client.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, AuditService, Module, get_audit_service
from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.exceptions import UnauthorizedError
from app.core.security import access_token_ttl_seconds
from app.core.session import SessionStore
from app.models.customer import Customer
from app.models.customer_account import CustomerAccount
from app.models.shop import Shop
from app.modules.customers.auth.dependencies import (
    clear_customer_refresh_cookie,
    get_current_customer,
    get_customer_refresh_token,
    get_customer_session_store,
    set_customer_refresh_cookie,
)
from app.modules.customers.auth.schemas import (
    CustomerAccountResponse,
    CustomerLoginRequest,
    CustomerLogoutResponse,
    CustomerTokenResponse,
)
from app.modules.customers.auth.service import customer_auth_service

router = APIRouter(prefix="/customer-auth", tags=["customer-auth"])
settings = get_settings()

DbDep = Annotated[AsyncSession, Depends(get_db_session)]
StoreDep = Annotated[SessionStore, Depends(get_customer_session_store)]
AuditDep = Annotated[AuditService, Depends(get_audit_service)]
CurrentCustomer = Annotated[CustomerAccount, Depends(get_current_customer)]


@router.post(
    "/login",
    response_model=CustomerTokenResponse,
    summary="Customer login with email and password",
)
async def customer_login(
    payload: CustomerLoginRequest,
    request: Request,
    response: Response,
    db: DbDep,
    store: StoreDep,
    audit: AuditDep,
) -> CustomerTokenResponse:
    """Authenticate a customer and issue access + refresh tokens.

    Requires shop_id in the request to ensure tenant isolation.
    """
    # We need shop_id from somewhere - could be from query param or header
    # For now, let's use a header or query param for shop identification
    shop_id_header = request.headers.get("x-shop-id")
    if not shop_id_header:
        raise UnauthorizedError("Shop ID required (x-shop-id header).")
    try:
        shop_id = int(shop_id_header)
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid shop ID.")

    customer_account = await customer_auth_service.authenticate(db, payload.email, payload.password, shop_id)
    if customer_account is None:
        await audit.record_from_request(
            request,
            action=AuditAction.LOGIN_FAILURE,
            module=Module.CUSTOMER,
            extra={"email": payload.email.strip().lower(), "shop_id": shop_id},
        )
        raise UnauthorizedError("Invalid email or password.")

    access_token, refresh_token, ttl = await customer_auth_service.issue_tokens(store, customer_account)
    set_customer_refresh_cookie(response, refresh_token, ttl)

    await audit.record_from_request(
        request,
        action=AuditAction.LOGIN_SUCCESS,
        module=Module.CUSTOMER,
        actor_user_id=None,
        actor_role="CUSTOMER",
        shop_id=shop_id,
        entity_type="customer_account",
        entity_id=str(customer_account.id),
    )

    # Load customer for response
    customer = await db.scalar(select(Customer).where(Customer.id == customer_account.customer_id))
    shop = await db.scalar(select(Shop).where(Shop.id == customer_account.shop_id))

    return CustomerTokenResponse(
        access_token=access_token,
        expires_in=access_token_ttl_seconds(),
        customer=CustomerAccountResponse.from_customer_account(customer_account, customer, shop),
    )


@router.post(
    "/refresh",
    response_model=CustomerTokenResponse,
    summary="Refresh the customer access token",
)
async def customer_refresh(
    request: Request,
    response: Response,
    db: DbDep,
    store: StoreDep,
    audit: AuditDep,
) -> CustomerTokenResponse:
    """Rotate the refresh session (cookie) and return a new access token."""
    refresh_token = get_customer_refresh_token(request)
    if not refresh_token:
        raise UnauthorizedError()

    rotated = await customer_auth_service.rotate_session(store, refresh_token)
    if rotated is None:
        raise UnauthorizedError("Session expired or invalid.")

    access_token, new_refresh_token, ttl, customer_account_id = rotated

    # Verify customer account still exists and is active
    customer_account = await db.scalar(
        select(CustomerAccount).where(CustomerAccount.id == customer_account_id)
    )
    if customer_account is None or customer_account.status != "active":
        await customer_auth_service.revoke_session(store, new_refresh_token)
        raise UnauthorizedError()

    set_customer_refresh_cookie(response, new_refresh_token, ttl)

    # Load customer and shop for response
    customer = await db.scalar(select(Customer).where(Customer.id == customer_account.customer_id))
    shop = await db.scalar(select(Shop).where(Shop.id == customer_account.shop_id))

    await audit.record_from_request(
        request,
        action=AuditAction.TOKEN_REFRESH,
        module=Module.CUSTOMER,
        actor_user_id=None,
        actor_role="CUSTOMER",
        shop_id=customer_account.shop_id,
        entity_type="customer_account",
        entity_id=str(customer_account.id),
    )

    return CustomerTokenResponse(
        access_token=access_token,
        expires_in=access_token_ttl_seconds(),
        customer=CustomerAccountResponse.from_customer_account(customer_account, customer, shop),
    )


@router.post(
    "/logout",
    response_model=CustomerLogoutResponse,
    summary="Logout and revoke the customer refresh session",
)
async def customer_logout(
    request: Request,
    response: Response,
    store: StoreDep,
    audit: AuditDep,
    customer_account: CurrentCustomer,
) -> CustomerLogoutResponse:
    """Revoke the caller's refresh session and clear the auth cookie."""
    refresh_token = get_customer_refresh_token(request)
    if refresh_token:
        await store.revoke(refresh_token)
    clear_customer_refresh_cookie(response)

    await audit.record_from_request(
        request,
        action=AuditAction.LOGOUT,
        module=Module.CUSTOMER,
        actor_user_id=None,
        actor_role="CUSTOMER",
        shop_id=customer_account.shop_id,
        entity_type="customer_account",
        entity_id=str(customer_account.id),
    )
    return CustomerLogoutResponse()


@router.get(
    "/me",
    response_model=CustomerAccountResponse,
    summary="Get the current authenticated customer",
)
async def customer_me(
    customer_account: CurrentCustomer,
    db: DbDep,
) -> CustomerAccountResponse:
    """Return the current authenticated customer's information."""
    customer = await db.scalar(select(Customer).where(Customer.id == customer_account.customer_id))
    shop = await db.scalar(select(Shop).where(Shop.id == customer_account.shop_id))

    return CustomerAccountResponse.from_customer_account(customer_account, customer, shop)