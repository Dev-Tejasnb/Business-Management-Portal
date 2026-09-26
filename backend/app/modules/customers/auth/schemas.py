"""Pydantic schemas for the customer authentication module.

Never expose password hashes or refresh tokens here. Refresh tokens travel in an
HTTP-only cookie and are not returned in response bodies.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.customer_account import CustomerAccountStatus
from app.models.customer import Customer
from app.models.shop import Shop


class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class CustomerAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    customer_id: int
    email: EmailStr
    status: CustomerAccountStatus
    failed_login_attempts: int
    locked_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_customer_account(
        cls,
        customer_account: CustomerAccount,
        customer: Customer | None = None,
        shop: Shop | None = None
    ) -> "CustomerAccountResponse":
        """Create response from customer account with optional related data."""
        return cls(
            id=customer_account.id,
            shop_id=customer_account.shop_id,
            customer_id=customer_account.customer_id,
            email=customer_account.email,
            status=customer_account.status,
            failed_login_attempts=customer_account.failed_login_attempts,
            locked_until=customer_account.locked_until,
            password_changed_at=customer_account.password_changed_at,
            last_login_at=customer_account.last_login_at,
            created_at=customer_account.created_at,
            updated_at=customer_account.updated_at,
        )


class CustomerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access token expires
    customer: CustomerAccountResponse


class CustomerLogoutResponse(BaseModel):
    message: str = "Successfully logged out."