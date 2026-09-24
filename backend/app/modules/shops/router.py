"""Shops/tenant API endpoints.

These endpoints exercise the centralized tenant-context and RBAC dependencies.
Note that ``shop_id`` always comes from the route path and access is verified
server-side via active membership — never from a request body.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, Module, get_audit_service
from app.core.database import get_db_session
from app.core.roles import PlatformRole, SHOP_VIEW, MEMBERSHIP_MANAGE, MEMBERSHIP_VIEW
from app.models.membership import ShopMembership
from app.models.user import User
from app.modules.auth.dependencies import (
    get_current_membership,
    get_current_user,
    require_permission,
    require_platform_permission,
    require_platform_role,
    require_shop_permission,
)
from app.modules.shops import service
from app.modules.shops.schemas import (
    ShopCreateRequest,
    ShopMembershipCreateRequest,
    ShopMembershipResponse,
    ShopResponse,
)

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db_session)]
AuditDep = Annotated[AuditService, Depends(get_audit_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/shops",
    response_model=ShopResponse,
    status_code=201,
    summary="Create a shop (platform)",
    dependencies=[Depends(require_platform_role(PlatformRole.OWNER, PlatformRole.ADMIN))],
)
async def create_shop(
    payload: ShopCreateRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
) -> ShopResponse:
    shop = await service.create_shop(
        db, code=payload.code, name=payload.name, slug=payload.slug
    )
    await audit.record(
        action="shop.created",
        module=Module.SHOP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        entity_type="shop",
        entity_id=str(shop.id),
        new_values={"code": shop.code, "name": shop.name, "slug": shop.slug},
    )
    return ShopResponse.model_validate(shop)


@router.get(
    "/shops",
    response_model=list[ShopResponse],
    summary="List shops (platform)",
    dependencies=[Depends(require_platform_permission(SHOP_VIEW))],
)
async def list_shops(db: DbDep) -> list[ShopResponse]:
    shops = await service.list_shops(db)
    return [ShopResponse.model_validate(s) for s in shops]


@router.get(
    "/shops/{shop_id}",
    response_model=ShopResponse,
    summary="Get a shop (platform or active member)",
)
async def get_shop(
    shop_id: int,
    db: DbDep,
    _access: Annotated[ShopMembership | None, Depends(require_permission(SHOP_VIEW))],
) -> ShopResponse:
    shop = await service.get_shop(db, shop_id)
    return ShopResponse.model_validate(shop)


@router.get(
    "/shops/{shop_id}/memberships/me",
    response_model=ShopMembershipResponse,
    summary="Get the caller's membership in a shop (proves tenant isolation)",
)
async def get_my_membership(
    membership: Annotated[ShopMembership, Depends(get_current_membership)],
) -> ShopMembershipResponse:
    return ShopMembershipResponse.from_membership(membership)


@router.post(
    "/shops/{shop_id}/memberships",
    response_model=ShopMembershipResponse,
    status_code=201,
    summary="Add a member to a shop",
)
async def create_membership(
    shop_id: int,
    payload: ShopMembershipCreateRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
    access: Annotated[ShopMembership | None, Depends(require_permission(MEMBERSHIP_MANAGE))],
) -> ShopMembershipResponse:
    shop = await service.get_shop(db, shop_id)
    target_user = await service.get_user_by_id(db, payload.user_id)
    membership = await service.create_membership(
        db, shop=shop, user=target_user, role=payload.role
    )
    actor_role = access.role if access is not None else user.platform_role
    await audit.record(
        action="membership.created",
        module=Module.MEMBERSHIP,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop.id,
        entity_type="shop_membership",
        entity_id=str(membership.id),
        new_values={"user_id": target_user.id, "role": payload.role.value},
    )
    return ShopMembershipResponse.from_membership(membership)


@router.get(
    "/shops/{shop_id}/memberships",
    response_model=list[ShopMembershipResponse],
    summary="List memberships for a shop",
    dependencies=[Depends(require_shop_permission(MEMBERSHIP_VIEW))],
)
async def list_memberships(
    shop_id: int,
    db: DbDep,
) -> list[ShopMembershipResponse]:
    memberships = await service.list_memberships(db, shop_id)
    return [ShopMembershipResponse.from_membership(m) for m in memberships]