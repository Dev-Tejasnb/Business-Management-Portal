"""Pydantic schemas for the service management module."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from typing_extensions import Literal

from app.core.roles import ShopRole
from app.models.service import ServiceStatus
from app.models.service_field import FieldType


class ServiceCategoryBase(BaseModel):
    """Base service category schema."""

    name: str = Field(min_length=2, max_length=100, description="Category name")
    slug: str = Field(min_length=2, max_length=120, description="URL-friendly identifier")
    description: Optional[str] = Field(default=None, max_length=500, description="Category description")
    is_active: bool = Field(default=True, description="Whether the category is active")


class ServiceCategoryCreate(ServiceCategoryBase):
    """Request to create a new service category."""


class ServiceCategoryUpdate(BaseModel):
    """Request to update a service category."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = Field(default=None)


class ServiceCategoryResponse(ServiceCategoryBase):
    """Service category response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ServiceBase(BaseModel):
    """Base service schema."""

    name: str = Field(min_length=2, max_length=255, description="Service name")
    slug: str = Field(min_length=2, max_length=120, description="URL-friendly identifier")
    description: Optional[str] = Field(default=None, max_length=2000, description="Service description")
    base_price: float = Field(gt=0, description="Base price of the service")
    estimated_processing_days: Optional[int] = Field(default=None, ge=0, description="Estimated processing time in days")
    category_id: Optional[int] = Field(default=None, description="Service category ID")
    status: Literal["active", "inactive", "archived"] = Field(default="active", description="Service lifecycle status")


class ServiceCreate(ServiceBase):
    """Request to create a new service."""


class ServiceUpdate(BaseModel):
    """Request to update a service."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    base_price: Optional[float] = Field(default=None, gt=0)
    estimated_processing_days: Optional[int] = Field(default=None, ge=0)
    category_id: Optional[int] = Field(default=None)
    status: Optional[Literal["active", "inactive", "archived"]] = Field(default=None)


class ServiceResponse(ServiceBase):
    """Service response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    created_at: datetime
    updated_at: datetime
    category_name: Optional[str] = Field(default=None, description="Name of the service category")


class ServiceListResponse(BaseModel):
    """Paginated service list response."""

    model_config = ConfigDict(from_attributes=True)

    items: List[ServiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ServiceRequiredDocumentBase(BaseModel):
    """Base service required document schema."""

    name: str = Field(min_length=2, max_length=255, description="Document name")
    description: Optional[str] = Field(default=None, max_length=500, description="Document description")
    is_mandatory: bool = Field(default=True, description="Whether the document is mandatory")
    allowed_file_types: Optional[List[str]] = Field(default=None, description="Allowed file extensions (e.g., ['pdf', 'jpg', 'png'])")
    max_file_size_mb: Optional[int] = Field(default=None, ge=1, le=100, description="Maximum file size in MB")


class ServiceRequiredDocumentCreate(ServiceRequiredDocumentBase):
    """Request to create a new service required document."""


class ServiceRequiredDocumentUpdate(BaseModel):
    """Request to update a service required document."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    is_mandatory: Optional[bool] = Field(default=None)
    allowed_file_types: Optional[List[str]] = Field(default=None)
    max_file_size_mb: Optional[int] = Field(default=None, ge=1, le=100)


class ServiceRequiredDocumentResponse(ServiceRequiredDocumentBase):
    """Service required document response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    created_at: datetime
    updated_at: datetime


class ServiceFieldBase(BaseModel):
    """Base service field schema."""

    name: str = Field(min_length=2, max_length=100, description="Field name")
    label: str = Field(min_length=2, max_length=255, description="Field label")
    field_type: Literal["text", "number", "date", "select", "textarea", "boolean"] = Field(default="text", description="Input field type")
    is_required: bool = Field(default=False, description="Whether the field is required")
    options: Optional[List[str]] = Field(default=None, description="Options for select fields")
    validation_rules: Optional[dict] = Field(default=None, description="Validation rules as JSON")
    sort_order: int = Field(default=0, description="Display order")


class ServiceFieldCreate(ServiceFieldBase):
    """Request to create a new service field."""


class ServiceFieldUpdate(BaseModel):
    """Request to update a service field."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    label: Optional[str] = Field(default=None, min_length=2, max_length=255)
    field_type: Optional[Literal["text", "number", "date", "select", "textarea", "boolean"]] = Field(default=None)
    is_required: Optional[bool] = Field(default=None)
    options: Optional[List[str]] = Field(default=None)
    validation_rules: Optional[dict] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)


class ServiceFieldResponse(ServiceFieldBase):
    """Service field response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    created_at: datetime
    updated_at: datetime