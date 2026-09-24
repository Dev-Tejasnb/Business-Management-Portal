"""Authentication API endpoints under /api/v1/auth.

Implements login, refresh (cookie-based rotation), logout and current-user.
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
from app.models.user import User
from app.modules.auth.dependencies import (
    clear_refresh_cookie,
    get_current_user,
    get_refresh_token,
    get_session_store,
    set_refresh_cookie,
)
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutResponse,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import auth_service

router = APIRouter()
settings = get_settings()

DbDep = Annotated[AsyncSession, Depends(get_db_session)]
StoreDep = Annotated[SessionStore, Depends(get_session_store)]
AuditDep = Annotated[AuditService, Depends(get_audit_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbDep,
    store: StoreDep,
    audit: AuditDep,
) -> TokenResponse:
    """Authenticate a user and issue access + refresh tokens."""
    user = await auth_service.authenticate(db, payload.email, payload.password)
    if user is None:
        await audit.record_from_request(
            request,
            action=AuditAction.LOGIN_FAILURE,
            module=Module.AUTH,
            extra={"email": payload.email.strip().lower()},
        )
        raise UnauthorizedError("Invalid email or password.")

    access_token, refresh_token, ttl = await auth_service.issue_tokens(store, user)
    set_refresh_cookie(response, refresh_token, ttl)

    await audit.record_from_request(
        request,
        action=AuditAction.LOGIN_SUCCESS,
        module=Module.AUTH,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        entity_type="user",
        entity_id=str(user.id),
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=access_token_ttl_seconds(),
        user=UserResponse.from_user(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh the access token",
)
async def refresh(
    request: Request,
    response: Response,
    db: DbDep,
    store: StoreDep,
    audit: AuditDep,
) -> TokenResponse:
    """Rotate the refresh session (cookie) and return a new access token."""
    refresh_token = get_refresh_token(request)
    if not refresh_token:
        raise UnauthorizedError()

    rotated = await auth_service.rotate_session(store, refresh_token)
    if rotated is None:
        raise UnauthorizedError("Session expired or invalid.")

    access_token, new_refresh_token, ttl, user_id = rotated
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        await auth_service.revoke_session(store, new_refresh_token)
        raise UnauthorizedError()

    set_refresh_cookie(response, new_refresh_token, ttl)
    return TokenResponse(
        access_token=access_token,
        expires_in=access_token_ttl_seconds(),
        user=UserResponse.from_user(user),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout and revoke the refresh session",
)
async def logout(
    request: Request,
    response: Response,
    store: StoreDep,
    audit: AuditDep,
    user: CurrentUser,
) -> LogoutResponse:
    """Revoke the caller's refresh session and clear the auth cookie."""
    refresh_token = get_refresh_token(request)
    if refresh_token:
        await store.revoke(refresh_token)
    clear_refresh_cookie(response)

    await audit.record_from_request(
        request,
        action=AuditAction.LOGOUT,
        module=Module.AUTH,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        entity_type="user",
        entity_id=str(user.id),
    )
    return LogoutResponse()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.from_user(user)