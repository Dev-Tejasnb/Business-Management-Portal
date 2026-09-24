"""Service Management API endpoints.

These endpoints provide shop-scoped service management:
- List, create, get, update, archive services
- Manage service categories
- Manage service required documents
- Manage service custom form fields
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, Module, get_audit_service
from app.core.database import get_db_session
from app.core.roles import (
    SERVICE_VIEW,
    SERVICE_CREATE,
    SERVICE_UPDATE,
    SERVICE_ARCHIVE,
)
from app.models.user import User
from app.modules.auth.dependencies import (
    get_current_membership,
    get_current_user,
    require_permission,
)
from app.modules.services import service
from app.modules.services.schemas import (
    ServiceCategoryCreate,
    ServiceCategoryResponse,
    ServiceCategoryUpdate,
    ServiceFieldCreate,
    ServiceFieldResponse,
    ServiceFieldUpdate,
    ServiceCreate,
    ServiceListResponse,
    ServiceResponse,
    ServiceUpdate,
    ServiceRequiredDocumentCreate,
    ServiceRequiredDocumentResponse,
    ServiceRequiredDocumentUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Service Categories Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/shops/{shop_id}/service-categories",
    response_model=List[ServiceCategoryResponse],
    summary="List service categories for a shop",
    dependencies=[Depends(require_permission(SERVICE_VIEW))],
)
async def list_service_categories(
    shop_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
) -> List[ServiceCategoryResponse]:
    """List service categories available to the shop.

    Requires STAFF_VIEW permission.
    """
    categories = await service.list_categories(db, is_active=is_active)
    return [ServiceCategoryResponse.model_validate(cat) for cat in categories]


@router.post(
    "/shops/{shop_id}/service-categories",
    response_model=ServiceCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new service category",
    dependencies=[Depends(require_permission(SERVICE_CREATE))],
)
async def create_service_category(
    shop_id: int,
    payload: ServiceCategoryCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_CREATE))],
) -> ServiceCategoryResponse:
    """Create a new service category.

    Requires STAFF_CREATE permission.
    """
    category = await service.create_category(
        db,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        is_active=payload.is_active,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service_category.created",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service_category",
        entity_id=str(category.id),
        new_values={
            "name": category.name,
            "slug": category.slug,
            "is_active": category.is_active,
        },
    )

    return ServiceCategoryResponse.model_validate(category)


@router.patch(
    "/shops/{shop_id}/service-categories/{category_id}",
    response_model=ServiceCategoryResponse,
    summary="Update a service category",
    dependencies=[Depends(require_permission(SERVICE_UPDATE))],
)
async def update_service_category(
    shop_id: int,
    category_id: int,
    payload: ServiceCategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_UPDATE))],
) -> ServiceCategoryResponse:
    """Update a service category.

    Requires STAFF_UPDATE permission.
    """
    category = await service.update_category(
        db,
        category_id=category_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        is_active=payload.is_active,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service_category.updated",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service_category",
        entity_id=str(category.id),
        old_values={},  # Simplified for now
        new_values=payload.model_dump(exclude_unset=True),
    )

    return ServiceCategoryResponse.model_validate(category)


# ---------------------------------------------------------------------------
# Services Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/shops/{shop_id}/services",
    response_model=ServiceListResponse,
    summary="List services in a shop",
    dependencies=[Depends(require_permission(SERVICE_VIEW))],
)
async def list_services(
    shop_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    search: Annotated[Optional[str], Query(description="Search by name or description")] = None,
    category_id: Annotated[Optional[int], Query(description="Filter by category ID")] = None,
    status: Annotated[Optional[str], Query(description="Filter by status")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> ServiceListResponse:
    """List services for a shop with search, category, and status filters.

    Requires STAFF_VIEW permission.
    """
    services, total = await service.list_services(
        db,
        shop_id=shop_id,
        search=search,
        category_id=category_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    service_responses = []
    for svc in services:
        resp = ServiceResponse.model_validate(svc)
        resp.category_name = svc.category.name if svc.category else None
        service_responses.append(resp)

    return ServiceListResponse(
        items=service_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/shops/{shop_id}/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new service",
    dependencies=[Depends(require_permission(SERVICE_CREATE))],
)
async def create_service(
    shop_id: int,
    payload: ServiceCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_CREATE))],
) -> ServiceResponse:
    """Create a new service in a shop.

    Requires STAFF_CREATE permission.
    """
    service_obj = await service.create_service(
        db,
        shop_id=shop_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        base_price=payload.base_price,
        estimated_processing_days=payload.estimated_processing_days,
        category_id=payload.category_id,
        status=payload.status,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.created",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service",
        entity_id=str(service_obj.id),
        new_values={
            "name": service_obj.name,
            "slug": service_obj.slug,
            "base_price": service_obj.base_price,
            "status": service_obj.status,
        },
    )

    resp = ServiceResponse.model_validate(service_obj)
    resp.category_name = service_obj.category.name if service_obj.category else None
    return resp


@router.get(
    "/shops/{shop_id}/services/{service_id}",
    response_model=ServiceResponse,
    summary="Get a service's details",
    dependencies=[Depends(require_permission(SERVICE_VIEW))],
)
async def get_service(
    shop_id: int,
    service_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _access: Annotated[object, Depends(require_permission(SERVICE_VIEW))],
) -> ServiceResponse:
    """Get a service by ID within a shop.

    Requires STAFF_VIEW permission.
    """
    service_obj = await service.get_service(db, shop_id=shop_id, service_id=service_id)
    resp = ServiceResponse.model_validate(service_obj)
    resp.category_name = service_obj.category.name if service_obj.category else None
    return resp


@router.patch(
    "/shops/{shop_id}/services/{service_id}",
    response_model=ServiceResponse,
    summary="Update a service",
    dependencies=[Depends(require_permission(SERVICE_UPDATE))],
)
async def update_service(
    shop_id: int,
    service_id: int,
    payload: ServiceUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_UPDATE))],
) -> ServiceResponse:
    """Update a service.

    Requires STAFF_UPDATE permission.
    """
    service_obj = await service.update_service(
        db,
        shop_id=shop_id,
        service_id=service_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        base_price=payload.base_price,
        estimated_processing_days=payload.estimated_processing_days,
        category_id=payload.category_id,
        status=payload.status,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.updated",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service",
        entity_id=str(service_obj.id),
        old_values={},  # Simplified for now
        new_values=payload.model_dump(exclude_unset=True),
    )

    resp = ServiceResponse.model_validate(service_obj)
    resp.category_name = service_obj.category.name if service_obj.category else None
    return resp


@router.delete(
    "/shops/{shop_id}/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive/delete a service",
    dependencies=[Depends(require_permission(SERVICE_ARCHIVE))],
)
async def delete_service(
    shop_id: int,
    service_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_ARCHIVE))],
) -> None:
    """Archive/delete a service (soft delete: set status to archived).

    Requires SERVICE_ARCHIVE permission.
    """
    await service.delete_service(db, shop_id=shop_id, service_id=service_id)

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.archived",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service",
        entity_id=str(service_id),
        old_values={"id": service_id},
        new_values={"status": "archived"},
    )


# ---------------------------------------------------------------------------
# Service Required Documents Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/shops/{shop_id}/services/{service_id}/required-documents",
    response_model=List[ServiceRequiredDocumentResponse],
    summary="List required documents for a service",
    dependencies=[Depends(require_permission(SERVICE_VIEW))],
)
async def list_required_documents(
    shop_id: int,
    service_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[ServiceRequiredDocumentResponse]:
    """List required documents for a service.

    Requires STAFF_VIEW permission.
    """
    docs = await service.list_required_documents(db, shop_id=shop_id, service_id=service_id)
    return [ServiceRequiredDocumentResponse.model_validate(doc) for doc in docs]


@router.post(
    "/shops/{shop_id}/services/{service_id}/required-documents",
    response_model=ServiceRequiredDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a required document to a service",
    dependencies=[Depends(require_permission(SERVICE_CREATE))],
)
async def add_required_document(
    shop_id: int,
    service_id: int,
    payload: ServiceRequiredDocumentCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_CREATE))],
) -> ServiceRequiredDocumentResponse:
    """Add a required document specification to a service.

    Requires STAFF_CREATE permission.
    """
    doc = await service.add_required_document(
        db,
        shop_id=shop_id,
        service_id=service_id,
        name=payload.name,
        description=payload.description,
        is_mandatory=payload.is_mandatory,
        allowed_file_types=payload.allowed_file_types,
        max_file_size_mb=payload.max_file_size_mb,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.required_document.added",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service_required_document",
        entity_id=str(doc.id),
        new_values={
            "name": doc.name,
            "is_mandatory": doc.is_mandatory,
        },
    )

    return ServiceRequiredDocumentResponse.model_validate(doc)


@router.patch(
    "/shops/{shop_id}/services/{service_id}/required-documents/{document_id}",
    response_model=ServiceRequiredDocumentResponse,
    summary="Update a required document",
    dependencies=[Depends(require_permission(SERVICE_UPDATE))],
)
async def update_required_document(
    shop_id: int,
    service_id: int,
    document_id: int,
    payload: ServiceRequiredDocumentUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_UPDATE))],
) -> ServiceRequiredDocumentResponse:
    """Update a required document specification.

    Requires STAFF_UPDATE permission.
    """
    doc = await service.update_required_document(
        db,
        shop_id=shop_id,
        service_id=service_id,
        document_id=document_id,
        name=payload.name,
        description=payload.description,
        is_mandatory=payload.is_mandatory,
        allowed_file_types=payload.allowed_file_types,
        max_file_size_mb=payload.max_file_size_mb,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.required_document.updated",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service_required_document",
        entity_id=str(doc.id),
        old_values={},  # Simplified
        new_values=payload.model_dump(exclude_unset=True),
    )

    return ServiceRequiredDocumentResponse.model_validate(doc)


@router.delete(
    "/shops/{shop_id}/services/{service_id}/required-documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a required document",
    dependencies=[Depends(require_permission(SERVICE_UPDATE))],
)
async def delete_required_document(
    shop_id: int,
    service_id: int,
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_UPDATE))],
) -> None:
    """Delete a required document specification.

    Requires STAFF_UPDATE permission.
    """
    await service.delete_required_document(db, shop_id=shop_id, service_id=service_id, document_id=document_id)

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.required_document.deleted",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service_required_document",
        entity_id=str(document_id),
        old_values={"id": document_id},
        new_values={},
    )


# ---------------------------------------------------------------------------
# Service Custom Form Fields Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/shops/{shop_id}/services/{service_id}/fields",
    response_model=List[ServiceFieldResponse],
    summary="List custom form fields for a service",
    dependencies=[Depends(require_permission(SERVICE_VIEW))],
)
async def list_service_fields(
    shop_id: int,
    service_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[ServiceFieldResponse]:
    """List custom form fields for a service.

    Requires STAFF_VIEW permission.
    """
    fields = await service.list_service_fields(db, shop_id=shop_id, service_id=service_id)
    return [ServiceFieldResponse.model_validate(field) for field in fields]


@router.post(
    "/shops/{shop_id}/services/{service_id}/fields",
    response_model=ServiceFieldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a custom form field to a service",
    dependencies=[Depends(require_permission(SERVICE_CREATE))],
)
async def add_service_field(
    shop_id: int,
    service_id: int,
    payload: ServiceFieldCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_CREATE))],
) -> ServiceFieldResponse:
    """Add a custom form field to a service.

    Requires STAFF_CREATE permission.
    """
    field = await service.add_service_field(
        db,
        shop_id=shop_id,
        service_id=service_id,
        name=payload.name,
        label=payload.label,
        field_type=payload.field_type,
        is_required=payload.is_required,
        options=payload.options,
        validation_rules=payload.validation_rules,
        sort_order=payload.sort_order,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.field.added",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service_field",
        entity_id=str(field.id),
        new_values={
            "name": field.name,
            "field_type": field.field_type,
            "is_required": field.is_required,
        },
    )

    return ServiceFieldResponse.model_validate(field)


@router.patch(
    "/shops/{shop_id}/services/{service_id}/fields/{field_id}",
    response_model=ServiceFieldResponse,
    summary="Update a custom form field",
    dependencies=[Depends(require_permission(SERVICE_UPDATE))],
)
async def update_service_field(
    shop_id: int,
    service_id: int,
    field_id: int,
    payload: ServiceFieldUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_UPDATE))],
) -> ServiceFieldResponse:
    """Update a custom form field.

    Requires STAFF_UPDATE permission.
    """
    field = await service.update_service_field(
        db,
        shop_id=shop_id,
        service_id=service_id,
        field_id=field_id,
        name=payload.name,
        label=payload.label,
        field_type=payload.field_type,
        is_required=payload.is_required,
        options=payload.options,
        validation_rules=payload.validation_rules,
        sort_order=payload.sort_order,
    )

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.field.updated",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service_field",
        entity_id=str(field.id),
        old_values={},  # Simplified
        new_values=payload.model_dump(exclude_unset=True),
    )

    return ServiceFieldResponse.model_validate(field)


@router.delete(
    "/shops/{shop_id}/services/{service_id}/fields/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom form field",
    dependencies=[Depends(require_permission(SERVICE_UPDATE))],
)
async def delete_service_field(
    shop_id: int,
    service_id: int,
    field_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    user: Annotated[User, Depends(get_current_user)],
    access: Annotated[object, Depends(require_permission(SERVICE_UPDATE))],
) -> None:
    """Delete a custom form field.

    Requires STAFF_UPDATE permission.
    """
    await service.delete_service_field(db, shop_id=shop_id, service_id=service_id, field_id=field_id)

    actor_role = access.role if hasattr(access, 'role') else user.platform_role
    await audit.record(
        action="service.field.deleted",
        module=Module.SERVICE,
        actor_user_id=user.id,
        actor_role=actor_role,
        shop_id=shop_id,
        entity_type="service_field",
        entity_id=str(field_id),
        old_values={"id": field_id},
        new_values={},
    )