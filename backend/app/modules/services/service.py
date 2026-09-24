"""Service management business logic and database queries."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.service import Service, ServiceStatus
from app.models.service_category import ServiceCategory
from app.models.service_field import ServiceField, ServiceRequiredDocument
from app.models.shop import Shop, ShopStatus


def normalize_slug(slug: str) -> str:
    """Normalize and validate a service or category slug."""
    normalized = slug.strip().lower()
    normalized = re.sub(r"[^a-z0-9\-]", "-", normalized)
    normalized = re.sub(r"\-+", "-", normalized)
    normalized = normalized.strip("-")

    if not normalized:
        raise ValidationError("Slug must contain at least 2 alphanumeric characters after normalization.")
    if len(normalized) > 120:
        raise ValidationError("Slug must be at most 120 characters.")
    if not re.search(r"[a-z0-9]", normalized):
        raise ValidationError("Slug must contain at least one letter or number.")

    return normalized


# ---------------------------------------------------------------------------
# Categories Management
# ---------------------------------------------------------------------------

async def list_categories(
    db: AsyncSession,
    *,
    is_active: Optional[bool] = None,
) -> List[ServiceCategory]:
    """List service categories."""
    query = select(ServiceCategory)
    if is_active is not None:
        query = query.where(ServiceCategory.is_active.is_(is_active))
    query = query.order_by(ServiceCategory.name.asc())
    return list((await db.scalars(query)).all())


async def get_category(db: AsyncSession, category_id: int) -> ServiceCategory:
    """Get category by ID."""
    category = await db.scalar(select(ServiceCategory).where(ServiceCategory.id == category_id))
    if category is None:
        raise NotFoundError("Service category not found.")
    return category


async def create_category(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    description: Optional[str] = None,
    is_active: bool = True,
) -> ServiceCategory:
    """Create a new service category."""
    clean_slug = normalize_slug(slug)

    existing = await db.scalar(
        select(ServiceCategory).where(
            or_(
                ServiceCategory.name == name.strip(),
                ServiceCategory.slug == clean_slug,
            )
        )
    )
    if existing is not None:
        raise ConflictError(f"Service category with name '{name}' or slug '{clean_slug}' already exists.")

    category = ServiceCategory(
        name=name.strip(),
        slug=clean_slug,
        description=description.strip() if description else None,
        is_active=is_active,
    )
    db.add(category)
    try:
        await db.flush()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Service category already exists.") from None

    return category


async def update_category(
    db: AsyncSession,
    category_id: int,
    *,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> ServiceCategory:
    """Update an existing service category."""
    category = await get_category(db, category_id)

    if name is not None:
        name_clean = name.strip()
        if name_clean != category.name:
            existing = await db.scalar(
                select(ServiceCategory).where(ServiceCategory.name == name_clean, ServiceCategory.id != category_id)
            )
            if existing is not None:
                raise ConflictError(f"Service category name '{name_clean}' is already in use.")
            category.name = name_clean

    if slug is not None:
        clean_slug = normalize_slug(slug)
        if clean_slug != category.slug:
            existing = await db.scalar(
                select(ServiceCategory).where(ServiceCategory.slug == clean_slug, ServiceCategory.id != category_id)
            )
            if existing is not None:
                raise ConflictError(f"Service category slug '{clean_slug}' is already in use.")
            category.slug = clean_slug

    if description is not None:
        category.description = description.strip() if description else None

    if is_active is not None:
        category.is_active = is_active

    await db.flush()
    await db.refresh(category)
    return category


# ---------------------------------------------------------------------------
# Services Management
# ---------------------------------------------------------------------------

async def list_services(
    db: AsyncSession,
    shop_id: int,
    *,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Service], int]:
    """List services for a shop with filtering and pagination."""
    query = (
        select(Service)
        .options(selectinload(Service.category))
        .where(Service.shop_id == shop_id)
    )

    if category_id is not None:
        query = query.where(Service.category_id == category_id)

    if status:
        query = query.where(Service.status == status)

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Service.name.ilike(term),
                Service.slug.ilike(term),
                Service.description.ilike(term),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate and order
    query = query.order_by(Service.id.desc()).offset((page - 1) * page_size).limit(page_size)
    services = list((await db.scalars(query)).all())

    return services, total


async def get_service(db: AsyncSession, shop_id: int, service_id: int) -> Service:
    """Get a service by ID within a shop."""
    service = await db.scalar(
        select(Service)
        .options(
            selectinload(Service.category),
            selectinload(Service.required_documents),
            selectinload(Service.fields),
        )
        .where(Service.id == service_id, Service.shop_id == shop_id)
    )
    if service is None:
        raise NotFoundError("Service not found.")
    return service


async def create_service(
    db: AsyncSession,
    *,
    shop_id: int,
    name: str,
    slug: str,
    description: Optional[str] = None,
    base_price: float,
    estimated_processing_days: Optional[int] = None,
    category_id: Optional[int] = None,
    status: str = ServiceStatus.ACTIVE.value,
) -> Service:
    """Create a new service in a shop."""
    clean_slug = normalize_slug(slug)

    # Verify category if provided
    if category_id is not None:
        await get_category(db, category_id)

    # Verify slug uniqueness within the shop
    existing = await db.scalar(
        select(Service).where(Service.shop_id == shop_id, Service.slug == clean_slug)
    )
    if existing is not None:
        raise ConflictError(f"Service with slug '{clean_slug}' already exists in this shop.")

    service = Service(
        shop_id=shop_id,
        name=name.strip(),
        slug=clean_slug,
        description=description.strip() if description else None,
        base_price=base_price,
        estimated_processing_days=estimated_processing_days,
        category_id=category_id,
        status=status,
    )
    db.add(service)
    try:
        await db.flush()
        await db.refresh(service)
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Service already exists in this shop.") from None

    # Load category relationship if assigned
    if service.category_id:
        await db.refresh(service, attribute_names=["category"])

    return service


async def update_service(
    db: AsyncSession,
    shop_id: int,
    service_id: int,
    *,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    base_price: Optional[float] = None,
    estimated_processing_days: Optional[int] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
) -> Service:
    """Update a service."""
    service = await get_service(db, shop_id, service_id)

    if name is not None:
        service.name = name.strip()

    if slug is not None:
        clean_slug = normalize_slug(slug)
        if clean_slug != service.slug:
            existing = await db.scalar(
                select(Service).where(
                    Service.shop_id == shop_id,
                    Service.slug == clean_slug,
                    Service.id != service_id,
                )
            )
            if existing is not None:
                raise ConflictError(f"Service with slug '{clean_slug}' already exists in this shop.")
            service.slug = clean_slug

    if category_id is not None:
        await get_category(db, category_id)
        service.category_id = category_id

    if description is not None:
        service.description = description.strip() if description else None

    if base_price is not None:
        service.base_price = base_price

    if estimated_processing_days is not None:
        service.estimated_processing_days = estimated_processing_days

    if status is not None:
        service.status = status

    await db.flush()
    await db.refresh(service, attribute_names=["category"])
    return service


async def delete_service(db: AsyncSession, shop_id: int, service_id: int) -> None:
    """Archive a service by setting its status to archived."""
    service = await get_service(db, shop_id, service_id)
    service.status = ServiceStatus.ARCHIVED.value
    await db.flush()
    await db.refresh(service)


# ---------------------------------------------------------------------------
# Required Documents Management
# ---------------------------------------------------------------------------

async def list_required_documents(db: AsyncSession, shop_id: int, service_id: int) -> List[ServiceRequiredDocument]:
    """List required documents for a service."""
    await get_service(db, shop_id, service_id)
    query = (
        select(ServiceRequiredDocument)
        .where(ServiceRequiredDocument.service_id == service_id)
        .order_by(ServiceRequiredDocument.id.asc())
    )
    return list((await db.scalars(query)).all())


async def add_required_document(
    db: AsyncSession,
    *,
    shop_id: int,
    service_id: int,
    name: str,
    description: Optional[str] = None,
    is_mandatory: bool = True,
    allowed_file_types: Optional[List[str]] = None,
    max_file_size_mb: Optional[int] = 10,
) -> ServiceRequiredDocument:
    """Add a required document specification to a service."""
    await get_service(db, shop_id, service_id)

    doc = ServiceRequiredDocument(
        service_id=service_id,
        name=name.strip(),
        description=description.strip() if description else None,
        is_mandatory=is_mandatory,
        allowed_file_types=allowed_file_types,
        max_file_size_mb=max_file_size_mb,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


async def update_required_document(
    db: AsyncSession,
    *,
    shop_id: int,
    service_id: int,
    document_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_mandatory: Optional[bool] = None,
    allowed_file_types: Optional[List[str]] = None,
    max_file_size_mb: Optional[int] = None,
) -> ServiceRequiredDocument:
    """Update a required document specification."""
    await get_service(db, shop_id, service_id)

    doc = await db.scalar(
        select(ServiceRequiredDocument).where(
            ServiceRequiredDocument.id == document_id,
            ServiceRequiredDocument.service_id == service_id,
        )
    )
    if doc is None:
        raise NotFoundError("Required document not found.")

    if name is not None:
        doc.name = name.strip()
    if description is not None:
        doc.description = description.strip() if description else None
    if is_mandatory is not None:
        doc.is_mandatory = is_mandatory
    if allowed_file_types is not None:
        doc.allowed_file_types = allowed_file_types
    if max_file_size_mb is not None:
        doc.max_file_size_mb = max_file_size_mb

    await db.flush()
    await db.refresh(doc)
    return doc


async def delete_required_document(db: AsyncSession, shop_id: int, service_id: int, document_id: int) -> None:
    """Delete a required document specification."""
    await get_service(db, shop_id, service_id)

    doc = await db.scalar(
        select(ServiceRequiredDocument).where(
            ServiceRequiredDocument.id == document_id,
            ServiceRequiredDocument.service_id == service_id,
        )
    )
    if doc is None:
        raise NotFoundError("Required document not found.")

    await db.delete(doc)
    await db.flush()


# ---------------------------------------------------------------------------
# Custom Form Fields Management
# ---------------------------------------------------------------------------

async def list_service_fields(db: AsyncSession, shop_id: int, service_id: int) -> List[ServiceField]:
    """List custom fields for a service."""
    await get_service(db, shop_id, service_id)
    query = (
        select(ServiceField)
        .where(ServiceField.service_id == service_id)
        .order_by(ServiceField.sort_order.asc(), ServiceField.id.asc())
    )
    return list((await db.scalars(query)).all())


async def add_service_field(
    db: AsyncSession,
    *,
    shop_id: int,
    service_id: int,
    name: str,
    label: str,
    field_type: str = "text",
    is_required: bool = False,
    options: Optional[List[str]] = None,
    validation_rules: Optional[dict] = None,
    sort_order: int = 0,
) -> ServiceField:
    """Add a custom form field to a service."""
    await get_service(db, shop_id, service_id)

    field = ServiceField(
        service_id=service_id,
        name=name.strip(),
        label=label.strip(),
        field_type=field_type,
        is_required=is_required,
        options=options,
        validation_rules=validation_rules,
        sort_order=sort_order,
    )
    db.add(field)
    await db.flush()
    await db.refresh(field)
    return field


async def update_service_field(
    db: AsyncSession,
    *,
    shop_id: int,
    service_id: int,
    field_id: int,
    name: Optional[str] = None,
    label: Optional[str] = None,
    field_type: Optional[str] = None,
    is_required: Optional[bool] = None,
    options: Optional[List[str]] = None,
    validation_rules: Optional[dict] = None,
    sort_order: Optional[int] = None,
) -> ServiceField:
    """Update a custom form field."""
    await get_service(db, shop_id, service_id)

    field = await db.scalar(
        select(ServiceField).where(
            ServiceField.id == field_id,
            ServiceField.service_id == service_id,
        )
    )
    if field is None:
        raise NotFoundError("Service field not found.")

    if name is not None:
        field.name = name.strip()
    if label is not None:
        field.label = label.strip()
    if field_type is not None:
        field.field_type = field_type
    if is_required is not None:
        field.is_required = is_required
    if options is not None:
        field.options = options
    if validation_rules is not None:
        field.validation_rules = validation_rules
    if sort_order is not None:
        field.sort_order = sort_order

    await db.flush()
    await db.refresh(field)
    return field


async def delete_service_field(db: AsyncSession, shop_id: int, service_id: int, field_id: int) -> None:
    """Delete a custom form field."""
    await get_service(db, shop_id, service_id)

    field = await db.scalar(
        select(ServiceField).where(
            ServiceField.id == field_id,
            ServiceField.service_id == service_id,
        )
    )
    if field is None:
        raise NotFoundError("Service field not found.")

    await db.delete(field)
    await db.flush()