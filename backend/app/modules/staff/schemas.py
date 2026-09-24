"""Pydantic schemas for the staff management module."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.roles import ShopRole


from enum import Enum


class AssignableStaffRole(str, Enum):
    """Staff roles that can be assigned via normal staff endpoints.

    SHOP_OWNER is explicitly excluded to prevent privilege escalation.
    Owner role must only be assigned via dedicated owner transfer endpoint.
    """
    MANAGER = "shop_manager"
    STAFF = "staff"
    FINANCIAL_STAFF = "financial_staff"


class StaffCreateRequest(BaseModel):
    """Request to create a new staff member (user + membership)."""

    email: EmailStr = Field(description="Email for the new user account")
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128, description="Initial password")
    role: AssignableStaffRole = Field(default=AssignableStaffRole.STAFF, description="Shop role for the membership (SHOP_OWNER cannot be assigned here)")


class StaffUpdateRequest(BaseModel):
    """Request to update staff profile info."""

    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)


class StaffRoleUpdateRequest(BaseModel):
    """Request to change staff role."""

    role: AssignableStaffRole = Field(description="New shop role (SHOP_OWNER cannot be assigned here)")


class StaffResponse(BaseModel):
    """Staff member response with user and membership details."""

    model_config = ConfigDict(from_attributes=True)

    membership_id: int
    user_id: int
    shop_id: int
    role: ShopRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user_email: EmailStr
    user_name: str


class StaffListResponse(BaseModel):
    """Paginated staff list response."""

    items: list[StaffResponse]
    total: int
    page: int
    page_size: int
    total_pages: int