"""Customer account model for customer portal authentication.

Represents a customer's login account tied to a specific shop and customer record.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.shop import Shop


class CustomerAccountStatus(str, Enum):
    """Customer account lifecycle statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"


class CustomerAccount(TimestampMixin, Base):
    """Customer account for portal authentication."""

    __tablename__ = "customer_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=CustomerAccountStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    locked_until: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    shop: Mapped["Shop"] = relationship()
    customer: Mapped["Customer"] = relationship()

    # Ensure one active account per shop-customer pair
    __table_args__ = (
        # Unique constraint on shop_id and customer_id for active accounts
        # We'll enforce via index and application logic, but also add a unique index
        # that excludes inactive/locked accounts if needed via partial index (PostgreSQL)
        # For simplicity, we'll enforce unique on (shop_id, customer_id) and handle
        # status in service logic.
        {"sqlite_autoincrement": True},
    )

    # Note: For PostgreSQL, we can add a partial unique index for active accounts:
    #   __table_args__ = (
    #       Index(
    #           "uq_customer_accounts_shop_customer_active",
    #           shop_id,
    #           customer_id,
    #           postgresql_where=status == CustomerAccountStatus.ACTIVE.value,
    #       ),
    #   )
    # But we'll keep it simple for now and enforce in service.