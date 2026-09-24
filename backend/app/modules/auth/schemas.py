"""Pydantic schemas for the authentication module.

Never expose password hashes or refresh tokens here. Refresh tokens travel in an
HTTP-only cookie and are not returned in response bodies.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.roles import PlatformRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    platform_role: PlatformRole | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            platform_role=user.platform_role_enum,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access token expires
    user: UserResponse


class LogoutResponse(BaseModel):
    message: str = "Successfully logged out."


class RefreshResponse(TokenResponse):
    pass