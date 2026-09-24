"""Pydantic schemas for the application management module."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, ConfigDict, Field, validator

from app.models.application import ApplicationStatus


class ApplicationBase(BaseModel):
    """Base application schema."""

    customer_id: int = Field(gt=0, description="Customer ID")
    service_id: int = Field(gt=0, description="Service ID")
    assigned_staff_id: Optional[int] = Field(default=None, gt=0, description="Assigned staff member ID")
    application_data: Optional[dict[str, Any]] = Field(default=None, description="Dynamic form data based on service fields")
    notes: Optional[str] = Field(default=None, description="Internal notes")
    status: Optional[ApplicationStatus] = Field(default=None, description="Application lifecycle status")


class ApplicationCreate(ApplicationBase):
    """Request to create a new application."""

    pass


class ApplicationUpdate(BaseModel):
    """Request to update an application."""

    application_data: Optional[dict[str, Any]] = Field(default=None, description="Dynamic form data based on service fields")
    notes: Optional[str] = Field(default=None, description="Internal notes")
    assigned_staff_id: Optional[int] = Field(default=None, gt=0, description="Assigned staff member ID")
    status: Optional[ApplicationStatus] = Field(default=None, description="Application lifecycle status")


class ApplicationResponse(ApplicationBase):
    """Application response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    application_number: str
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = Field(default=None, description="Customer name")
    customer_mobile: Optional[str] = Field(default=None, description="Customer mobile number")
    service_name: Optional[str] = Field(default=None, description="Service name")
    assigned_staff_name: Optional[str] = Field(default=None, description="Assigned staff member name")


class ApplicationListResponse(BaseModel):
    """Paginated application list response."""

    model_config = ConfigDict(from_attributes=True)

    items: List[ApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int