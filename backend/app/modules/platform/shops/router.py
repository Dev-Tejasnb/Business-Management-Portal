"""Platform Shop Management API endpoints.

These endpoints provide platform-level shop lifecycle management:
- Create, list, get, update shops
- Activate/deactivate/suspend shops
- Transfer primary ownership
- Assign/unassign platform managers
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, Module, get_audit_service
from app.core.database import get_db_session
from app.core.roles import (
    PlatformRole,
    SHOP_VIEW,
    SHOP_CREATE,
    SHOP_UPDATE,
    SHOP_ACTIVATE,
    SHOP_DEACTIVATE,
    SHOP_ASSIGN_MANAGER,
    MEMBERSHIP_VIEW,
)
from app.models.user import User
from app.modules.auth.dependencies import (
    get_current_user,
    require_permission,
    require_platform_permission,
    require_platform_role,
)
from app.modules.platform.shops import service
from app.modules.platform.shops.schemas import (
    PlatformManagerAssignmentRequest,
    PlatformManagerAssignmentUpdateRequest,
    PlatformManagerResponse,
    ShopActivateRequest,
    ShopCreateRequest,
    ShopDeactivateRequest,
    ShopListResponse,
    ShopOwnerTransferRequest,
    ShopResponse,
    ShopUpdateRequest,
)

router = APIRouter(prefix="/platform/shops", tags=["platform-shops"])

DbDep = Annotated[AsyncSession, Depends(get_db_session)]
AuditDep = Annotated[AuditService, Depends(get_audit_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=ShopResponse,
    status_code=201,
    summary="Create a new shop (platform owner/admin)",
    dependencies=[Depends(require_platform_role(PlatformRole.OWNER, PlatformRole.ADMIN))],
)
async def create_shop(
    payload: ShopCreateRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
) -> ShopResponse:
    """Create a shop with auto-generated code and unique slug.

    Requires Platform Owner or Admin role.
    """
    shop = await service.create_shop(
        db,
        name=payload.name,
        slug=payload.slug,
        owner_user_id=payload.owner_user_id,
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
    "",
    response_model=ShopListResponse,
    summary="List shops with filters and pagination",
    dependencies=[Depends(require_platform_permission(SHOP_VIEW))],
)
async def list_shops(
    db: DbDep,
    user: CurrentUser,
    search: Annotated[Optional[str], Query(description="Search by name, code, or slug")] = None,
    status: Annotated[Optional[str], Query(description="Filter by status")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> ShopListResponse:
    """List shops with search, status filter, and pagination.

    Platform Managers only see their assigned shops.
    """
    shops, total = await service.list_shops(
        db,
        search=search,
        status=status,
        page=page,
        page_size=page_size,
        user=user,
    )

    # Load primary owner for each shop
    from sqlalchemy import select
    from app.models.membership import ShopMembership
    from app.core.roles import ShopRole

    shop_responses = []
    for shop in shops:
        owner = await service.get_shop_primary_owner(db, shop.id)
        shop_responses.append(
            ShopResponse(
                id=shop.id,
                code=shop.code,
                name=shop.name,
                slug=shop.slug,
                status=shop.status,
                created_at=shop.created_at,
                updated_at=shop.updated_at,
                primary_owner_id=owner.id if owner else None,
                primary_owner_email=owner.email if owner else None,
                primary_owner_name=owner.full_name if owner else None,
            )
        )

    return ShopListResponse(
        items=shop_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/{shop_id}",
    response_model=ShopResponse,
    summary="Get shop details with primary owner",
)
async def get_shop(
    shop_id: int,
    db: DbDep,
    _access: Annotated[object, Depends(require_permission(SHOP_VIEW))],
) -> ShopResponse:
    """Get a shop by ID.

    Requires SHOP_VIEW permission via platform or shop membership.
    """
    shop = await service.get_shop_by_id(db, shop_id)
    owner = await service.get_shop_primary_owner(db, shop_id)
    return ShopResponse(
        id=shop.id,
        code=shop.code,
        name=shop.name,
        slug=shop.slug,
        status=shop.status,
        created_at=shop.created_at,
        updated_at=shop.updated_at,
        primary_owner_id=owner.id if owner else None,
        primary_owner_email=owner.email if owner else None,
        primary_owner_name=owner.full_name if owner else None,
    )


@router.patch(
    "/{shop_id}",
    response_model=ShopResponse,
    summary="Update shop basic info",
)
async def update_shop(
    shop_id: int,
    payload: ShopUpdateRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
    _access: Annotated[object, Depends(require_permission(SHOP_UPDATE))],
) -> ShopResponse:
    """Update shop name and/or slug.

    Requires SHOP_UPDATE permission.
    """
    old_values = {"name": None, "slug": None}
    shop = await service.get_shop_by_id(db, shop_id)
    if payload.name is not None:
        old_values["name"] = shop.name
    if payload.slug is not None:
        old_values["slug"] = shop.slug

    shop = await service.update_shop(
        db,
        shop_id,
        name=payload.name,
        slug=payload.slug,
    )
    new_values = {"name": shop.name, "slug": shop.slug}
    await audit.record(
        action="shop.updated",
        module=Module.SHOP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="shop",
        entity_id=str(shop.id),
        old_values={k: v for k, v in old_values.items() if v is not None},
        new_values=new_values,
    )
    return ShopResponse.model_validate(shop)


@router.post(
    "/{shop_id}/activate",
    response_model=ShopResponse,
    summary="Activate a shop",
    dependencies=[Depends(require_platform_permission(SHOP_ACTIVATE))],
)
async def activate_shop(
    shop_id: int,
    _payload: ShopActivateRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
) -> ShopResponse:
    """Activate a shop (set status to 'active').

    Requires SHOP_ACTIVATE platform permission (Owner/Admin).
    """
    shop = await service.get_shop_by_id(db, shop_id)
    old_status = shop.status

    shop = await service.activate_shop(db, shop_id)

    await audit.record(
        action="shop.activated",
        module=Module.SHOP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="shop",
        entity_id=str(shop.id),
        old_values={"status": old_status},
        new_values={"status": shop.status},
    )
    return ShopResponse.model_validate(shop)


@router.post(
    "/{shop_id}/deactivate",
    response_model=ShopResponse,
    summary="Deactivate or suspend a shop",
    dependencies=[Depends(require_platform_permission(SHOP_DEACTIVATE))],
)
async def deactivate_shop(
    shop_id: int,
    payload: ShopDeactivateRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
) -> ShopResponse:
    """Deactivate or suspend a shop.

    Requires SHOP_DEACTIVATE platform permission (Owner/Admin).
    """
    shop = await service.get_shop_by_id(db, shop_id)
    old_status = shop.status

    shop = await service.deactivate_shop(db, shop_id, payload.status)

    await audit.record(
        action="shop.deactivated",
        module=Module.SHOP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="shop",
        entity_id=str(shop.id),
        old_values={"status": old_status},
        new_values={"status": shop.status},
    )
    return ShopResponse.model_validate(shop)


@router.post(
    "/{shop_id}/owner",
    response_model=ShopResponse,
    summary="Transfer primary shop ownership",
    dependencies=[Depends(require_platform_permission(SHOP_UPDATE))],
)
async def transfer_owner(
    shop_id: int,
    payload: ShopOwnerTransferRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
) -> ShopResponse:
    """Transfer primary shop ownership to another active member.

    Requires SHOP_UPDATE permission. The new owner must be an active member
    of the shop. Audits the ownership transfer.
    """
    old_owner = await service.get_shop_primary_owner(db, shop_id)

    shop, new_owner, old_owner_obj = await service.transfer_shop_owner(
        db,
        shop_id,
        payload.new_owner_user_id,
    )

    await audit.record(
        action="shop.owner_changed",
        module=Module.SHOP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="shop",
        entity_id=str(shop.id),
        old_values={"primary_owner_id": old_owner_obj.id if old_owner_obj else None},
        new_values={"primary_owner_id": new_owner.id},
    )
    return ShopResponse.model_validate(shop)


# ============================================================================
# Platform Manager Assignment Endpoints
# ============================================================================

@router.get(
    "/{shop_id}/managers",
    response_model=list[PlatformManagerResponse],
    summary="List platform managers assigned to a shop",
    dependencies=[Depends(require_platform_permission(SHOP_VIEW))],
)
async def list_shop_managers(
    shop_id: int,
    db: DbDep,
) -> list[PlatformManagerResponse]:
    """List all platform managers assigned to a shop."""
    assignments = await service.list_shop_managers(db, shop_id)
    return [
        PlatformManagerResponse(
            id=a.id,
            user_id=a.user_id,
            shop_id=a.shop_id,
            is_active=a.is_active,
            created_at=a.created_at,
            updated_at=a.updated_at,
            user_email=a.user.email if a.user else None,
            user_name=a.user.full_name if a.user else None,
            user_platform_role=a.user.platform_role if a.user else None,
        )
        for a in assignments
    ]


@router.post(
    "/{shop_id}/managers",
    response_model=PlatformManagerResponse,
    status_code=201,
    summary="Assign a platform manager to a shop",
    dependencies=[Depends(require_platform_role(PlatformRole.OWNER))],
)
async def assign_manager(
    shop_id: int,
    payload: PlatformManagerAssignmentRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
) -> PlatformManagerResponse:
    """Assign a Platform Manager to a shop.

    Requires Platform Owner role (SHOP_ASSIGN_MANAGER permission).
    User must have platform_role='platform_manager'.
    """
    assignment = await service.assign_platform_manager(
        db,
        shop_id,
        payload.user_id,
        payload.is_active,
    )

    await audit.record(
        action="shop.manager_assigned",
        module=Module.SHOP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="platform_manager_shop",
        entity_id=str(assignment.id),
        new_values={"user_id": assignment.user_id, "is_active": assignment.is_active},
    )

    return PlatformManagerResponse(
        id=assignment.id,
        user_id=assignment.user_id,
        shop_id=assignment.shop_id,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        user_email=assignment.user.email if assignment.user else None,
        user_name=assignment.user.full_name if assignment.user else None,
        user_platform_role=assignment.user.platform_role if assignment.user else None,
    )


@router.delete(
    "/{shop_id}/managers/{user_id}",
    status_code=204,
    summary="Unassign a platform manager from a shop",
    dependencies=[Depends(require_platform_role(PlatformRole.OWNER))],
)
async def unassign_manager(
    shop_id: int,
    user_id: int,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
) -> None:
    """Unassign a Platform Manager from a shop.

    Requires Platform Owner role.
    """
    await service.unassign_platform_manager(db, shop_id, user_id)

    await audit.record(
        action="shop.manager_unassigned",
        module=Module.SHOP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="platform_manager_shop",
        entity_id=str(user_id),
        old_values={"user_id": user_id},
    )


@router.patch(
    "/{shop_id}/managers/{user_id}",
    response_model=PlatformManagerResponse,
    summary="Update a platform manager assignment status",
    dependencies=[Depends(require_platform_role(PlatformRole.OWNER))],
)
async def update_manager_assignment(
    shop_id: int,
    user_id: int,
    payload: PlatformManagerAssignmentUpdateRequest,
    db: DbDep,
    audit: AuditDep,
    user: CurrentUser,
) -> PlatformManagerResponse:
    """Update the active status of a Platform Manager assignment.

    Requires Platform Owner role.
    """
    assignment = await service.update_platform_manager_assignment(
        db,
        shop_id,
        user_id,
        payload.is_active,
    )

    await audit.record(
        action="shop.manager_assignment_updated",
        module=Module.SHOP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="platform_manager_shop",
        entity_id=str(assignment.id),
        new_values={"is_active": assignment.is_active},
    )

    return PlatformManagerResponse(
        id=assignment.id,
        user_id=assignment.user_id,
        shop_id=assignment.shop_id,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        user_email=assignment.user.email if assignment.user else None,
        user_name=assignment.user.full_name if assignment.user else None,
        user_platform_role=assignment.user.platform_role if assignment.user else None,
    )