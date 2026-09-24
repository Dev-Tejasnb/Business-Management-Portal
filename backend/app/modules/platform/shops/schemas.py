"""Pydantic schemas for the platform shops module."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ShopCreateRequest(BaseModel):
    """Request to create a new shop with auto-generated code."""

    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=120)
    owner_user_id: Optional[int] = Field(default=None, description="Optional initial shop owner user ID")


class ShopUpdateRequest(BaseModel):
    """Request to update shop basic info."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=120)


class ShopActivateRequest(BaseModel):
    """Request to activate a shop."""

    pass


class ShopDeactivateRequest(BaseModel):
    """Request to deactivate/suspend a shop."""

    status: str = Field(pattern="^(inactive|suspended)$", description="Target status: inactive or suspended")


class ShopOwnerTransferRequest(BaseModel):
    """Request to transfer primary shop ownership."""

    new_owner_user_id: int = Field(description="User ID of the new owner (must be active member)")


class PlatformManagerAssignmentRequest(BaseModel):
    """Request to assign a platform manager to a shop."""

    user_id: int = Field(description="User ID of platform manager")
    is_active: bool = Field(default=True)


class PlatformManagerAssignmentUpdateRequest(BaseModel):
    """Request to update a platform manager assignment."""

    is_active: bool


class ShopResponse(BaseModel):
    """Shop response with all fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime
    primary_owner_id: Optional[int] = None
    primary_owner_email: Optional[str] = None
    primary_owner_name: Optional[str] = None


class ShopListResponse(BaseModel):
    """Paginated shop list response."""

    items: list[ShopResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PlatformManagerResponse(BaseModel):
    """Platform manager assignment response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    shop_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_platform_role: Optional[str] = None