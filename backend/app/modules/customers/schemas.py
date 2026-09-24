"""Pydantic schemas for the customer management module."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.customer import CustomerStatus


class CustomerBase(BaseModel):
    """Base customer schema."""

    name: str = Field(min_length=1, max_length=255, description="Customer name")
    mobile: str = Field(min_length=10, max_length=20, description="Mobile number (will be normalized)")
    email: Optional[EmailStr] = Field(default=None, max_length=255, description="Email address")
    address: Optional[str] = Field(default=None, description="Customer address")
    notes: Optional[str] = Field(default=None, description="Internal notes")
    primary_staff_id: Optional[int] = Field(default=None, description="Primary staff member ID")
    status: CustomerStatus = Field(default=CustomerStatus.ACTIVE, description="Customer lifecycle status")


class CustomerCreate(CustomerBase):
    """Request to create a new customer."""

    pass


class CustomerUpdate(BaseModel):
    """Request to update a customer."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    mobile: Optional[str] = Field(default=None, min_length=10, max_length=20)
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    primary_staff_id: Optional[int] = Field(default=None)
    status: Optional[CustomerStatus] = Field(default=None)


class CustomerResponse(CustomerBase):
    """Customer response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    created_at: datetime
    updated_at: datetime
    primary_staff_name: Optional[str] = Field(default=None, description="Name of primary staff member")


class CustomerListResponse(BaseModel):
    """Paginated customer list response."""

    model_config = ConfigDict(from_attributes=True)

    items: List[CustomerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int