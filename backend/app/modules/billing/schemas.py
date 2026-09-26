"""Billing and Payment Pydantic schemas."""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Annotated

from pydantic import BaseModel, Field, ConfigDict


# Base schemas for billing items
class BillingItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    amount: Annotated[Decimal, Field(ge=0, decimal_places=2)]
    is_service_item: bool = False
    service_id: Optional[int] = None
    sort_order: int = 0


class BillingItemCreate(BillingItemBase):
    pass


class BillingItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    amount: Optional[Annotated[Decimal, Field(ge=0, decimal_places=2)]] = None
    is_service_item: Optional[bool] = None
    service_id: Optional[int] = None
    sort_order: Optional[int] = None


class BillingItemResponse(BillingItemBase):
    id: int
    billing_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Billing schemas
class BillingBase(BaseModel):
    notes: Optional[str] = None


class BillingCreate(BillingBase):
    application_id: int
    # Non-service charges are handled via billing items
    # Discount is handled via separate fields
    discount_type: Optional[str] = None  # "fixed" or "percentage"
    discount_value: Optional[Annotated[Decimal, Field(ge=0, decimal_places=2)]] = None
    discount_reason: Optional[str] = None
    items: List[BillingItemCreate] = Field(..., min_length=1)


class BillingUpdate(BaseModel):
    notes: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Annotated[Decimal, Field(ge=0, decimal_places=2)]] = None
    discount_reason: Optional[str] = None
    # Items are managed separately via dedicated endpoints


class BillingResponse(BillingBase):
    id: int
    shop_id: int
    application_id: int
    customer_id: int
    invoice_number: str
    service_amount: Annotated[Decimal, Field(decimal_places=2)]
    non_service_charges: Annotated[Decimal, Field(decimal_places=2)]
    subtotal: Annotated[Decimal, Field(decimal_places=2)]
    discount_type: Optional[str] = None
    discount_value: Optional[Annotated[Decimal, Field(decimal_places=2)]] = None
    discount_amount: Annotated[Decimal, Field(decimal_places=2)]
    discount_reason: Optional[str] = None
    total_amount: Annotated[Decimal, Field(decimal_places=2)]
    amount_paid: Annotated[Decimal, Field(decimal_places=2)]
    balance_amount: Annotated[Decimal, Field(decimal_places=2)]
    payment_status: str
    billing_status: str
    created_by: int
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[BillingItemResponse] = []
    application_number: Optional[str] = None
    customer_name: Optional[str] = None
    service_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BillingListResponse(BaseModel):
    items: List[BillingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Payment schemas
class PaymentBase(BaseModel):
    amount: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    payment_method: str  # "cash", "upi", "card", "bank_transfer", "other"
    reference_number: Optional[str] = None
    reference_exception: bool = False
    reference_exception_reason: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    amount: Optional[Annotated[Decimal, Field(gt=0, decimal_places=2)]] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    reference_exception: Optional[bool] = None
    reference_exception_reason: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(PaymentBase):
    id: int
    shop_id: int
    billing_id: int
    recorded_by: int
    paid_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    recorder_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentListResponse(BaseModel):
    items: List[PaymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Invoice number generation response
class InvoiceNumberResponse(BaseModel):
    invoice_number: str


# Billing calculation preview
class BillingCalculationPreview(BaseModel):
    service_amount: Annotated[Decimal, Field(decimal_places=2)]
    non_service_charges: Annotated[Decimal, Field(decimal_places=2)]
    subtotal: Annotated[Decimal, Field(decimal_places=2)]
    discount_type: Optional[str] = None
    discount_value: Optional[Annotated[Decimal, Field(decimal_places=2)]] = None
    discount_amount: Annotated[Decimal, Field(decimal_places=2)]
    total_amount: Annotated[Decimal, Field(decimal_places=2)]


# Receipt schemas (Phase 10)
class ReceiptBase(BaseModel):
    """Base receipt schema."""
    receipt_number: str
    receipt_type: str
    storage_key: Optional[str] = None
    status: str


class ReceiptCreate(BaseModel):
    """Schema for creating a receipt (generating PDF)."""
    pass


class ReceiptResponse(ReceiptBase):
    """Receipt response schema."""
    id: int
    shop_id: int
    billing_id: Optional[int] = None
    payment_id: Optional[int] = None
    generated_at: datetime
    generated_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CommunicationHistoryBase(BaseModel):
    """Base communication history schema."""
    channel: str
    recipient: str
    subject: Optional[str] = None
    status: str


class CommunicationHistoryResponse(CommunicationHistoryBase):
    """Communication history response schema."""
    id: int
    shop_id: int
    customer_id: Optional[int] = None
    application_id: Optional[int] = None
    payment_id: Optional[int] = None
    billing_id: Optional[int] = None
    receipt_id: Optional[int] = None
    provider: Optional[str] = None
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SendReceiptRequest(BaseModel):
    """Request schema for sending a receipt."""
    channel: str = Field(..., pattern="^(email|whatsapp|sms)$")
    recipient: str = Field(..., min_length=1, max_length=255)
    subject: Optional[str] = Field(None, max_length=500)


class SendReceiptResponse(BaseModel):
    """Response schema for sending a receipt."""
    id: int
    channel: str
    recipient: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime
    error_message: Optional[str] = None