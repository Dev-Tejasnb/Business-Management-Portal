"""Customer Management API endpoints.

These endpoints provide shop-scoped customer management:
- List, create, get, update customers
- Archive/restore customers (soft delete)
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, Module, get_audit_service
from app.core.database import get_db_session
from app.core.roles import (
    CUSTOMER_VIEW,
    CUSTOMER_CREATE,
    CUSTOMER_UPDATE,
    CUSTOMER_ARCHIVE,
)
from app.models.user import User
from app.modules.auth.dependencies import (
    get_current_membership,
    get_current_user,
    require_permission,
)
from app.modules.customers import service
from app.modules.customers.schemas import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)

router = APIRouter()


@router.get(
    "/shops/{shop_id}/customers",
    response_model=CustomerListResponse,
    summary="List customers for a shop",
    dependencies=[Depends(require_permission(CUSTOMER_VIEW))],
)
async def list_customers(
    shop_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    search: Annotated[Optional[str], Query(description="Search by name, mobile, or email")] = None,
    status: Annotated[Optional[str], Query(description="Filter by status")] = None,
    primary_staff_id: Annotated[Optional[int], Query(description="Filter by primary staff ID")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
) -> CustomerListResponse:
    """List customers for a shop with search, status, and staff filters."""
    # Convert status string to enum if provided
    status_enum = None
    if status:
        try:
            from app.models.customer import CustomerStatus
            status_enum = CustomerStatus(status)
        except ValueError:
            # Invalid status - ignore filter
            pass

    customers, total = await service.list_customers(
        db,
        shop_id=shop_id,
        search=search,
        status=status_enum,
        primary_staff_id=primary_staff_id,
        page=page,
        page_size=page_size,
    )

    customer_responses = [CustomerResponse.model_validate(cust) for cust in customers]

    return CustomerListResponse(
        items=customer_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/shops/{shop_id}/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
    dependencies=[Depends(require_permission(CUSTOMER_CREATE))],
)
async def create_customer(
    shop_id: int,
    payload: CustomerCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(CUSTOMER_CREATE))],
) -> CustomerResponse:
    """Create a new customer in a shop.

    Requires CUSTOMER_CREATE permission.
    """
    customer = await service.create_customer(
        db,
        shop_id=shop_id,
        name=payload.name,
        mobile=payload.mobile,
        email=payload.email,
        address=payload.address,
        notes=payload.notes,
        primary_staff_id=payload.primary_staff_id,
        actor_user_id=user.id,
        actor_role=user.platform_role.value if hasattr(user.platform_role, 'value') else str(user.platform_role),
        ip_address=getattr(user, 'ip_address', None),
        user_agent=getattr(user, 'user_agent', None),
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="customer.created",
        module=Module.CUSTOMER,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="customer",
        entity_id=str(customer.id),
        new_values={
            "name": customer.name,
            "mobile": customer.mobile,
            "email": customer.email,
            "status": customer.status,
            "primary_staff_id": customer.primary_staff_id,
        },
    )

    return CustomerResponse.model_validate(customer)


@router.get(
    "/shops/{shop_id}/customers/{customer_id}",
    response_model=CustomerResponse,
    summary="Get a customer's details",
    dependencies=[Depends(require_permission(CUSTOMER_VIEW))],
)
async def get_customer(
    shop_id: int,
    customer_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _access: Annotated[object, Depends(require_permission(CUSTOMER_VIEW))],
) -> CustomerResponse:
    """Get a customer by ID within a shop.

    Requires CUSTOMER_VIEW permission.
    """
    customer = await service.get_customer(db, customer_id=customer_id, shop_id=shop_id)
    if not customer:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerResponse.model_validate(customer)


@router.patch(
    "/shops/{shop_id}/customers/{customer_id}",
    response_model=CustomerResponse,
    summary="Update a customer",
    dependencies=[Depends(require_permission(CUSTOMER_UPDATE))],
)
async def update_customer(
    shop_id: int,
    customer_id: int,
    payload: CustomerUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(CUSTOMER_UPDATE))],
) -> CustomerResponse:
    """Update a customer.

    Requires CUSTOMER_UPDATE permission.
    """
    customer = await service.update_customer(
        db,
        shop_id=shop_id,
        customer_id=customer_id,
        name=payload.name,
        mobile=payload.mobile,
        email=payload.email,
        address=payload.address,
        notes=payload.notes,
        primary_staff_id=payload.primary_staff_id,
        status=payload.status,
        actor_user_id=user.id,
        actor_role=user.platform_role.value if hasattr(user.platform_role, 'value') else str(user.platform_role),
        ip_address=getattr(user, 'ip_address', None),
        user_agent=getattr(user, 'user_agent', None),
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="customer.updated",
        module=Module.CUSTOMER,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="customer",
        entity_id=str(customer.id),
        old_values={},  # Simplified for now
        new_values=payload.model_dump(exclude_unset=True),
    )

    return CustomerResponse.model_validate(customer)


@router.patch(
    "/shops/{shop_id}/customers/{customer_id}/archive",
    response_model=CustomerResponse,
    summary="Archive a customer",
    dependencies=[Depends(require_permission(CUSTOMER_ARCHIVE))],
)
async def archive_customer(
    shop_id: int,
    customer_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(CUSTOMER_ARCHIVE))],
) -> CustomerResponse:
    """Archive (soft delete) a customer.

    Requires CUSTOMER_ARCHIVE permission.
    """
    customer = await service.archive_customer(
        db,
        shop_id=shop_id,
        customer_id=customer_id,
        actor_user_id=user.id,
        actor_role=user.platform_role.value if hasattr(user.platform_role, 'value') else str(user.platform_role),
        ip_address=getattr(user, 'ip_address', None),
        user_agent=getattr(user, 'user_agent', None),
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="customer.archived",
        module=Module.CUSTOMER,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="customer",
        entity_id=str(customer.id),
        old_values={"status": "active"},
        new_values={"status": "archived"},
    )

    return CustomerResponse.model_validate(customer)


@router.patch(
    "/shops/{shop_id}/customers/{customer_id}/restore",
    response_model=CustomerResponse,
    summary="Restore an archived customer",
    dependencies=[Depends(require_permission(CUSTOMER_ARCHIVE))],
)
async def restore_customer(
    shop_id: int,
    customer_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(CUSTOMER_ARCHIVE))],
) -> CustomerResponse:
    """Restore an archived customer.

    Requires CUSTOMER_ARCHIVE permission (same as archive for symmetry).
    """
    customer = await service.restore_customer(
        db,
        shop_id=shop_id,
        customer_id=customer_id,
        actor_user_id=user.id,
        actor_role=user.platform_role.value if hasattr(user.platform_role, 'value') else str(user.platform_role),
        ip_address=getattr(user, 'ip_address', None),
        user_agent=getattr(user, 'user_agent', None),
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="customer.restored",
        module=Module.CUSTOMER,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="customer",
        entity_id=str(customer.id),
        old_values={"status": "archived"},
        new_values={"status": "active"},
    )

    return CustomerResponse.model_validate(customer)