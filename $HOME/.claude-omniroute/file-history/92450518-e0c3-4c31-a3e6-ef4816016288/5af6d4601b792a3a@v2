"""Communication models.

This file defines the communication history model for tracking sent communications.
The Receipt model is defined in receipt.py to avoid circular imports.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.billing import Billing, Payment
    from app.models.shop import Shop
    from app.models.customer import Customer
    from app.models.application import Application
    from app.models.user import User
    from app.models.receipt import Receipt


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
    receipt: Mapped["Receipt | None"] = relationship()

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