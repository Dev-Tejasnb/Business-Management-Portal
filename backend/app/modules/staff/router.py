"""Staff Management API endpoints.

These endpoints provide shop-scoped staff management:
- List, create, get, update staff
- Change staff role
- Activate/deactivate staff membership
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, Module, get_audit_service
from app.core.database import get_db_session
from app.core.roles import (
    ShopRole,
    STAFF_VIEW,
    STAFF_CREATE,
    STAFF_UPDATE,
    STAFF_ROLE_UPDATE,
    STAFF_ACTIVATE,
    STAFF_DEACTIVATE,
)
from app.models.user import User
from app.modules.auth.dependencies import (
    get_current_membership,
    get_current_user,
    require_permission,
)
from app.modules.staff import service
from app.modules.staff.schemas import (
    StaffCreateRequest,
    StaffListResponse,
    StaffResponse,
    StaffRoleUpdateRequest,
    StaffUpdateRequest,
)

router = APIRouter()


@router.get(
    "/shops/{shop_id}/staff",
    response_model=StaffListResponse,
    summary="List staff members in a shop",
    dependencies=[Depends(require_permission(STAFF_VIEW))],
)
async def list_staff(
    shop_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    search: Annotated[Optional[str], Query(description="Search by name or email")] = None,
    role: Annotated[Optional[ShopRole], Query(description="Filter by role")] = None,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> StaffListResponse:
    """List staff memberships for a shop with search, role, and active filters.

    Requires STAFF_VIEW permission.
    """
    memberships, total = await service.list_staff(
        db,
        shop_id,
        search=search,
        role=role.value if role else None,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    staff_responses = [
        StaffResponse(
            membership_id=m.id,
            user_id=m.user_id,
            shop_id=m.shop_id,
            role=m.role_enum,
            is_active=m.is_active,
            created_at=m.created_at,
            updated_at=m.updated_at,
            user_email=m.user.email,
            user_name=m.user.full_name,
        )
        for m in memberships
    ]

    return StaffListResponse(
        items=staff_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/shops/{shop_id}/staff",
    response_model=StaffResponse,
    status_code=201,
    summary="Add a staff member to a shop",
    dependencies=[Depends(require_permission(STAFF_CREATE))],
)
async def create_staff(
    shop_id: int,
    payload: StaffCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(STAFF_CREATE))],
) -> StaffResponse:
    """Create a new staff member (creates User + ShopMembership).

    Requires STAFF_CREATE permission. Creates user account with Argon2id hashed password.
    """
    user_obj, membership = await service.create_staff(
        db,
        shop_id=shop_id,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        role=payload.role,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="staff.created",
        module=Module.MEMBERSHIP,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="shop_membership",
        entity_id=str(membership.id),
        new_values={
            "user_id": user_obj.id,
            "role": payload.role.value,
            "email": payload.email,
        },
    )

    return StaffResponse(
        membership_id=membership.id,
        user_id=user_obj.id,
        shop_id=membership.shop_id,
        role=membership.role_enum,
        is_active=membership.is_active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        user_email=user_obj.email,
        user_name=user_obj.full_name,
    )


@router.get(
    "/shops/{shop_id}/staff/{membership_id}",
    response_model=StaffResponse,
    summary="Get a staff member's details",
    dependencies=[Depends(require_permission(STAFF_VIEW))],
)
async def get_staff(
    shop_id: int,
    membership_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _access: Annotated[object, Depends(require_permission(STAFF_VIEW))],
) -> StaffResponse:
    """Get a staff member by membership ID.

    Requires STAFF_VIEW permission.
    """
    membership = await service.get_staff_membership(db, shop_id, membership_id)
    return StaffResponse(
        membership_id=membership.id,
        user_id=membership.user_id,
        shop_id=membership.shop_id,
        role=membership.role_enum,
        is_active=membership.is_active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        user_email=membership.user.email,
        user_name=membership.user.full_name,
    )


@router.patch(
    "/shops/{shop_id}/staff/{membership_id}",
    response_model=StaffResponse,
    summary="Update a staff member's profile",
    dependencies=[Depends(require_permission(STAFF_UPDATE))],
)
async def update_staff(
    shop_id: int,
    membership_id: int,
    payload: StaffUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(STAFF_UPDATE))],
) -> StaffResponse:
    """Update a staff member's profile information.

    Requires STAFF_UPDATE permission.
    """
    # Get current membership to capture old values for audit
    membership_before = await service.get_staff_membership(db, shop_id, membership_id)
    old_values = {"full_name": membership_before.user.full_name}
    if payload.full_name is None:
        # No change to full_name, so don't audit this field
        old_values.pop("full_name", None)

    membership = await service.update_staff_profile(
        db,
        shop_id=shop_id,
        membership_id=membership_id,
        full_name=payload.full_name,
    )

    new_values = {}
    if payload.full_name is not None:
        new_values["full_name"] = membership.user.full_name

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="staff.updated",
        module=Module.MEMBERSHIP,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="shop_membership",
        entity_id=str(membership.id),
        old_values=old_values,
        new_values=new_values,
    )

    return StaffResponse(
        membership_id=membership.id,
        user_id=membership.user_id,
        shop_id=membership.shop_id,
        role=membership.role_enum,
        is_active=membership.is_active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        user_email=membership.user.email,
        user_name=membership.user.full_name,
    )


@router.patch(
    "/shops/{shop_id}/staff/{membership_id}/role",
    response_model=StaffResponse,
    summary="Change a staff member's role",
    dependencies=[Depends(require_permission(STAFF_ROLE_UPDATE))],
)
async def change_staff_role(
    shop_id: int,
    membership_id: int,
    payload: StaffRoleUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(STAFF_ROLE_UPDATE))],
) -> StaffResponse:
    """Change a staff member's role within the shop.

    Requires STAFF_ROLE_UPDATE permission. Prevents removing the only shop owner.
    """
    membership = await service.get_staff_membership(db, shop_id, membership_id)
    old_role = membership.role_enum

    membership = await service.change_staff_role(
        db,
        shop_id=shop_id,
        membership_id=membership_id,
        new_role=payload.role,
    )

    await audit.record(
        action="staff.role_changed",
        module=Module.MEMBERSHIP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="shop_membership",
        entity_id=str(membership.id),
        old_values={"role": old_role.value},
        new_values={"role": membership.role_enum.value},
    )

    return StaffResponse(
        membership_id=membership.id,
        user_id=membership.user_id,
        shop_id=membership.shop_id,
        role=membership.role_enum,
        is_active=membership.is_active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        user_email=membership.user.email,
        user_name=membership.user.full_name,
    )


@router.post(
    "/shops/{shop_id}/staff/{membership_id}/activate",
    response_model=StaffResponse,
    status_code=200,
    summary="Activate a staff membership",
    dependencies=[Depends(require_permission(STAFF_ACTIVATE))],
)
async def activate_staff(
    shop_id: int,
    membership_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    _access: Annotated[object, Depends(require_permission(STAFF_ACTIVATE))],
) -> StaffResponse:
    """Activate a staff membership (set is_active=True).

    Requires STAFF_ACTIVATE permission.
    """
    membership = await service.activate_staff(db, shop_id, membership_id)

    await audit.record(
        action="staff.activated",
        module=Module.MEMBERSHIP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="shop_membership",
        entity_id=str(membership.id),
        old_values={"is_active": False},
        new_values={"is_active": True},
    )

    return StaffResponse(
        membership_id=membership.id,
        user_id=membership.user_id,
        shop_id=membership.shop_id,
        role=membership.role_enum,
        is_active=membership.is_active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        user_email=membership.user.email,
        user_name=membership.user.full_name,
    )


@router.post(
    "/shops/{shop_id}/staff/{membership_id}/deactivate",
    response_model=StaffResponse,
    status_code=200,
    summary="Deactivate a staff membership",
    dependencies=[Depends(require_permission(STAFF_DEACTIVATE))],
)
async def deactivate_staff(
    shop_id: int,
    membership_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    _access: Annotated[object, Depends(require_permission(STAFF_DEACTIVATE))],
) -> StaffResponse:
    """Deactivate a staff membership (set is_active=False).

    Requires STAFF_DEACTIVATE permission. Prevents deactivating the only shop owner.
    """
    membership = await service.deactivate_staff(db, shop_id, membership_id)

    await audit.record(
        action="staff.deactivated",
        module=Module.MEMBERSHIP,
        actor_user_id=user.id,
        actor_role=user.platform_role,
        shop_id=shop_id,
        entity_type="shop_membership",
        entity_id=str(membership.id),
        old_values={"is_active": True},
        new_values={"is_active": False},
    )

    return StaffResponse(
        membership_id=membership.id,
        user_id=membership.user_id,
        shop_id=membership.shop_id,
        role=membership.role_enum,
        is_active=membership.is_active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        user_email=membership.user.email,
        user_name=membership.user.full_name,
    )