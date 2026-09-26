"""Receipt and Communication History models.

Represents generated receipts (invoices and payment receipts) and communication
history for sending receipts via email/WhatsApp/SMS.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.billing import Billing, Payment
    from app.models.shop import Shop
    from app.models.customer import Customer
    from app.models.application import Application
    from app.models.user import User


class ReceiptType(str, Enum):
    """Receipt type enumeration."""

    INVOICE = "invoice"
    PAYMENT_RECEIPT = "payment_receipt"


class ReceiptStatus(str, Enum):
    """Receipt status enumeration."""

    GENERATED = "generated"
    SENT = "sent"
    FAILED = "failed"
    ARCHIVED = "archived"


class CommunicationChannel(str, Enum):
    """Communication channel enumeration."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"


class CommunicationStatus(str, Enum):
    """Communication status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Receipt(TimestampMixin, Base):
    """Generated receipt (invoice or payment receipt) record."""

    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    billing_id: Mapped[int | None] = mapped_column(
        ForeignKey("billings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    receipt_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    receipt_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )
    generated_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=ReceiptStatus.GENERATED.value, nullable=False, index=True
    )

    # Relationships
    shop: Mapped["Shop"] = relationship()
    billing: Mapped["Billing | None"] = relationship()
    payment: Mapped["Payment | None"] = relationship()
    generator: Mapped["User"] = relationship()
    communications: Mapped[list["CommunicationHistory"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "receipt_type IN ('invoice', 'payment_receipt')",
            name="ck_receipt_type",
        ),
        CheckConstraint(
            "status IN ('generated', 'sent', 'failed', 'archived')",
            name="ck_receipt_status",
        ),
        # Ensure exactly one of billing_id or payment_id is set
        CheckConstraint(
            "(billing_id IS NOT NULL) != (payment_id IS NOT NULL)",
            name="ck_receipt_has_reference",
        ),
    )

    @property
    def receipt_type_enum(self) -> ReceiptType:
        return ReceiptType(self.receipt_type)

    @property
    def status_enum(self) -> ReceiptStatus:
        return ReceiptStatus(self.status)


class CommunicationHistory(TimestampMixin, Base):
    """Communication history for sent receipts."""

    __tablename__ = "communication_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    billing_id: Mapped[int | None] = mapped_column(
        ForeignKey("billings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    receipt_id: Mapped[int | None] = mapped_column(
        ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=CommunicationStatus.PENDING.value, nullable=False, index=True
    )
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    shop: Mapped["Shop"] = relationship()
    customer: Mapped["Customer | None"] = relationship()
    application: Mapped["Application | None"] = relationship()
    payment: Mapped["Payment | None"] = relationship()
    billing: Mapped["Billing | None"] = relationship()
    receipt: Mapped["Receipt | None"] = relationship(back_populates="communications")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'whatsapp', 'sms')",
            name="ck_communication_channel",
        ),
        CheckConstraint(
            "status IN ('pending', 'queued', 'sent', 'failed', 'cancelled')",
            name="ck_communication_status",
        ),
        # Composite index for duplicate-send protection
        Index(
            "ix_communication_duplicate_check",
            "receipt_id",
            "channel",
            "recipient",
            "created_at",
        ),
    )

    @property
    def channel_enum(self) -> CommunicationChannel:
        return CommunicationChannel(self.channel)

    @property
    def status_enum(self) -> CommunicationStatus:
        return CommunicationStatus(self.status)