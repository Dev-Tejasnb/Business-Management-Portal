"""Pydantic schemas for the shops/tenant module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.roles import ShopRole
from app.models.shop import ShopStatus


class ShopCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=120)


class ShopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    slug: str
    status: ShopStatus
    created_at: datetime
    updated_at: datetime


class ShopMembershipCreateRequest(BaseModel):
    user_id: int
    role: ShopRole


class ShopMembershipResponse(BaseModel):
    id: int
    user_id: int
    shop_id: int
    role: ShopRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user_email: EmailStr
    user_name: str

    @classmethod
    def from_membership(cls, membership) -> "ShopMembershipResponse":
        return cls(
            id=membership.id,
            user_id=membership.user_id,
            shop_id=membership.shop_id,
            role=membership.role_enum,
            is_active=membership.is_active,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
            user_email=membership.user.email,
            user_name=membership.user.full_name,
        )