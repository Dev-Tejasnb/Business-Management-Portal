"""Billing and Payment models.

Represents invoices/bills and payments for applications in a shop.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.shop import Shop
    from app.models.user import User


class BillingStatus(str, Enum):
    """Billing/Invoice lifecycle statuses."""

    DRAFT = "draft"
    ISSUED = "issued"
    VOID = "void"


class PaymentStatus(str, Enum):
    """Payment statuses for billing records."""

    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


class PaymentMethod(str, Enum):
    """Supported payment methods."""

    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class DiscountType(str, Enum):
    """Discount calculation types."""

    FIXED = "fixed"
    PERCENTAGE = "percentage"


class Billing(TimestampMixin, Base):
    """Billing/Invoice record for an application in a shop."""

    __tablename__ = "billings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    # Monetary values - use Numeric for precision
    service_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    non_service_charges: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    discount_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discount_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    discount_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    balance_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), default=PaymentStatus.UNPAID.value, nullable=False, index=True
    )
    billing_status: Mapped[str] = mapped_column(
        String(20), default=BillingStatus.DRAFT.value, nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    shop: Mapped["Shop"] = relationship()
    application: Mapped["Application"] = relationship()
    customer: Mapped["Customer"] = relationship()
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    updater: Mapped["User | None"] = relationship(foreign_keys=[updated_by])
    items: Mapped[list["BillingItem"]] = relationship(
        back_populates="billing", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="billing", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "service_amount >= 0",
            name="ck_billing_service_amount_nonneg",
        ),
        CheckConstraint(
            "non_service_charges >= 0",
            name="ck_billing_non_service_charges_nonneg",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_billing_discount_amount_nonneg",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_billing_total_amount_nonneg",
        ),
        CheckConstraint(
            "amount_paid >= 0",
            name="ck_billing_amount_paid_nonneg",
        ),
        CheckConstraint(
            "balance_amount >= 0",
            name="ck_billing_balance_amount_nonneg",
        ),
        CheckConstraint(
            "amount_paid <= total_amount",
            name="ck_billing_paid_not_exceed_total",
        ),
        CheckConstraint(
            "billing_status IN ('draft', 'issued', 'void')",
            name="ck_billing_status",
        ),
        CheckConstraint(
            "payment_status IN ('unpaid', 'partially_paid', 'paid')",
            name="ck_payment_status",
        ),
    )

    @property
    def payment_status_enum(self) -> PaymentStatus:
        return PaymentStatus(self.payment_status)

    @property
    def billing_status_enum(self) -> BillingStatus:
        return BillingStatus(self.billing_status)

    def recalculate_totals(self) -> None:
        """Recalculate derived monetary fields from line items and discount."""
        # Sum all billing items
        self.service_amount = sum(
            (item.amount for item in self.items if item.is_service_item),
            Decimal("0.00"),
        )
        self.non_service_charges = sum(
            (item.amount for item in self.items if not item.is_service_item),
            Decimal("0.00"),
        )
        self.subtotal = self.service_amount + self.non_service_charges

        # Apply discount
        if self.discount_type and self.discount_value is not None:
            if self.discount_type == DiscountType.FIXED.value:
                self.discount_amount = min(self.discount_value, self.subtotal)
            elif self.discount_type == DiscountType.PERCENTAGE.value:
                self.discount_amount = (
                    (self.subtotal * self.discount_value / Decimal("100")).quantize(
                        Decimal("0.01")
                    )
                )
        else:
            self.discount_amount = Decimal("0.00")

        self.total_amount = self.subtotal - self.discount_amount
        self.balance_amount = self.total_amount - self.amount_paid

        # Update payment status
        if self.amount_paid == Decimal("0.00"):
            self.payment_status = PaymentStatus.UNPAID.value
        elif self.amount_paid >= self.total_amount:
            self.payment_status = PaymentStatus.PAID.value
        else:
            self.payment_status = PaymentStatus.PARTIALLY_PAID.value


class BillingItem(TimestampMixin, Base):
    """Line item on a billing record."""

    __tablename__ = "billing_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    billing_id: Mapped[int] = mapped_column(
        ForeignKey("billings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_service_item: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    billing: Mapped["Billing"] = relationship(back_populates="items")
    service: Mapped["Service | None"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name="ck_billing_item_amount_nonneg",
        ),
    )


class Payment(TimestampMixin, Base):
    """Payment recorded against a billing/invoice."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    billing_id: Mapped[int] = mapped_column(
        ForeignKey("billings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    reference_number: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    reference_exception: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    reference_exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(), nullable=False
    )

    # Relationships
    shop: Mapped["Shop"] = relationship()
    billing: Mapped["Billing"] = relationship(back_populates="payments")
    recorder: Mapped["User"] = relationship()

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_payment_amount_positive",
        ),
        CheckConstraint(
            "payment_method IN ('cash', 'upi', 'card', 'bank_transfer', 'other')",
            name="ck_payment_method",
        ),
    )

    @property
    def payment_method_enum(self) -> PaymentMethod:
        return PaymentMethod(self.payment_method)

    def is_digital_payment(self) -> bool:
        """Check if payment method is digital (requires reference unless exception)."""
        return self.payment_method in (
            PaymentMethod.UPI.value,
            PaymentMethod.CARD.value,
            PaymentMethod.BANK_TRANSFER.value,
            PaymentMethod.OTHER.value,
        )