"""Application Management API endpoints.

These endpoints provide shop-scoped application management:
- List, create, get, update applications
- Assign/reassign/unassign staff
- Update application status
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, Module, get_audit_service
from app.core.database import get_db_session
from app.core.roles import (
    APPLICATION_VIEW,
    APPLICATION_CREATE,
    APPLICATION_UPDATE,
)
from app.models.application import ApplicationStatus
from app.models.user import User
from app.modules.auth.dependencies import (
    get_current_membership,
    get_current_user,
    require_permission,
)
from app.modules.applications.service import ApplicationService
from app.modules.applications.schemas import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
)

router = APIRouter()


@router.get(
    "/shops/{shop_id}/applications",
    response_model=ApplicationListResponse,
    summary="List applications for a shop",
    dependencies=[Depends(require_permission(APPLICATION_VIEW))],
)
async def list_applications(
    shop_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    search: Annotated[Optional[str], Query(description="Search by application number, customer, or service")] = None,
    status: Annotated[Optional[str], Query(description="Filter by status")] = None,
    service_id: Annotated[Optional[int], Query(description="Filter by service ID")] = None,
    customer_id: Annotated[Optional[int], Query(description="Filter by customer ID")] = None,
    assigned_staff_id: Annotated[Optional[int], Query(description="Filter by assigned staff ID")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
) -> ApplicationListResponse:
    """List applications for a shop with search, status, service, customer, and staff filters."""
    # Convert status string to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = ApplicationStatus(status)
        except ValueError:
            # Invalid status - ignore filter
            pass

    service = ApplicationService(db)
    applications, total = await service.list_applications(
        shop_id=shop_id,
        search=search,
        status=status_enum,
        service_id=service_id,
        customer_id=customer_id,
        assigned_staff_id=assigned_staff_id,
        page=page,
        page_size=page_size,
    )

    application_responses = []
    for app in applications:
        resp = ApplicationResponse.model_validate(app)
        if app.customer:
            resp.customer_name = app.customer.name
            resp.customer_mobile = app.customer.mobile
        if app.service:
            resp.service_name = app.service.name
        if app.assigned_staff:
            resp.assigned_staff_name = app.assigned_staff.full_name or app.assigned_staff.email
        application_responses.append(resp)

    return ApplicationListResponse(
        items=application_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/shops/{shop_id}/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new application",
    dependencies=[Depends(require_permission(APPLICATION_CREATE))],
)
async def create_application(
    shop_id: int,
    payload: ApplicationCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(APPLICATION_CREATE))],
) -> ApplicationResponse:
    """Create a new application in a shop.

    Requires APPLICATION_CREATE permission.
    """
    service = ApplicationService(db)
    application = await service.create_application(
        shop_id=shop_id,
        customer_id=payload.customer_id,
        service_id=payload.service_id,
        assigned_staff_id=payload.assigned_staff_id,
        application_data=payload.application_data,
        notes=payload.notes,
        actor_user_id=user.id,
        actor_role=user.platform_role.value if hasattr(user.platform_role, 'value') else str(user.platform_role),
        ip_address=getattr(user, 'ip_address', None),
        user_agent=getattr(user, 'user_agent', None),
    )

    resp = ApplicationResponse.model_validate(application)
    if application.customer:
        resp.customer_name = application.customer.name
        resp.customer_mobile = application.customer.mobile
    if application.service:
        resp.service_name = application.service.name
    if application.assigned_staff:
        resp.assigned_staff_name = application.assigned_staff.full_name or application.assigned_staff.email

    return resp


@router.get(
    "/shops/{shop_id}/applications/{application_id}",
    response_model=ApplicationResponse,
    summary="Get an application's details",
    dependencies=[Depends(require_permission(APPLICATION_VIEW))],
)
async def get_application(
    shop_id: int,
    application_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _access: Annotated[object, Depends(require_permission(APPLICATION_VIEW))],
) -> ApplicationResponse:
    """Get an application by ID within a shop.

    Requires APPLICATION_VIEW permission.
    """
    service = ApplicationService(db)
    application = await service.get_application(application_id=application_id, shop_id=shop_id)
    if not application:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Application not found")

    resp = ApplicationResponse.model_validate(application)
    if application.customer:
        resp.customer_name = application.customer.name
        resp.customer_mobile = application.customer.mobile
    if application.service:
        resp.service_name = application.service.name
    if application.assigned_staff:
        resp.assigned_staff_name = application.assigned_staff.full_name or application.assigned_staff.email

    return resp


@router.patch(
    "/shops/{shop_id}/applications/{application_id}",
    response_model=ApplicationResponse,
    summary="Update an application",
    dependencies=[Depends(require_permission(APPLICATION_UPDATE))],
)
async def update_application(
    shop_id: int,
    application_id: int,
    payload: ApplicationUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(APPLICATION_UPDATE))],
) -> ApplicationResponse:
    """Update an application.

    Requires APPLICATION_UPDATE permission.
    """
    service = ApplicationService(db)
    application = await service.update_application(
        application_id=application_id,
        shop_id=shop_id,
        application_data=payload.application_data,
        notes=payload.notes,
        assigned_staff_id=payload.assigned_staff_id,
        status=payload.status,
        actor_user_id=user.id,
        actor_role=user.platform_role.value if hasattr(user.platform_role, 'value') else str(user.platform_role),
        ip_address=getattr(user, 'ip_address', None),
        user_agent=getattr(user, 'user_agent', None),
    )

    resp = ApplicationResponse.model_validate(application)
    if application.customer:
        resp.customer_name = application.customer.name
        resp.customer_mobile = application.customer.mobile
    if application.service:
        resp.service_name = application.service.name
    if application.assigned_staff:
        resp.assigned_staff_name = application.assigned_staff.full_name or application.assigned_staff.email

    return resp


@router.patch(
    "/shops/{shop_id}/applications/{application_id}/assign",
    response_model=ApplicationResponse,
    summary="Assign or unassign staff",
    dependencies=[Depends(require_permission(APPLICATION_UPDATE))],
)
async def assign_staff(
    shop_id: int,
    application_id: int,
    payload: dict,  # Expect {"assigned_staff_id": int | None}
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(APPLICATION_UPDATE))],
) -> ApplicationResponse:
    """Assign or unassign staff to an application.

    Requires APPLICATION_UPDATE permission.
    """
    assigned_staff_id = payload.get("assigned_staff_id")
    service = ApplicationService(db)
    application = await service.assign_staff(
        application_id=application_id,
        shop_id=shop_id,
        assigned_staff_id=assigned_staff_id,
        actor_user_id=user.id,
        actor_role=user.platform_role.value if hasattr(user.platform_role, 'value') else str(user.platform_role),
        ip_address=getattr(user, 'ip_address', None),
        user_agent=getattr(user, 'user_agent', None),
    )

    resp = ApplicationResponse.model_validate(application)
    if application.customer:
        resp.customer_name = application.customer.name
        resp.customer_mobile = application.customer.mobile
    if application.service:
        resp.service_name = application.service.name
    if application.assigned_staff:
        resp.assigned_staff_name = application.assigned_staff.full_name or application.assigned_staff.email

    return resp


@router.patch(
    "/shops/{shop_id}/applications/{application_id}/status",
    response_model=ApplicationResponse,
    summary="Update application status",
    dependencies=[Depends(require_permission(APPLICATION_UPDATE))],
)
async def update_status(
    shop_id: int,
    application_id: int,
    payload: dict,  # Expect {"status": "enquiry" | "applied" | ...}
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(APPLICATION_UPDATE))],
) -> ApplicationResponse:
    """Update application status.

    Requires APPLICATION_UPDATE permission.
    """
    status_str = payload.get("status")
    if not status_str:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Status is required")

    try:
        status_enum = ApplicationStatus(status_str)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid status: {status_str}")

    service = ApplicationService(db)
    application = await service.update_status(
        application_id=application_id,
        shop_id=shop_id,
        status=status_enum,
        actor_user_id=user.id,
        actor_role=user.platform_role.value if hasattr(user.platform_role, 'value') else str(user.platform_role),
        ip_address=getattr(user, 'ip_address', None),
        user_agent=getattr(user, 'user_agent', None),
    )

    resp = ApplicationResponse.model_validate(application)
    if application.customer:
        resp.customer_name = application.customer.name
        resp.customer_mobile = application.customer.mobile
    if application.service:
        resp.service_name = application.service.name
    if application.assigned_staff:
        resp.assigned_staff_name = application.assigned_staff.full_name or application.assigned_staff.email

    return resp