"""Customer model.

Represents a customer belonging to a shop.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.user import User
    from app.models.application import Application


class CustomerStatus(str, Enum):
    """Customer lifecycle statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Customer(TimestampMixin, Base):
    """Customer belonging to a shop."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=CustomerStatus.ACTIVE.value, nullable=False, index=True
    )
    primary_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    shop: Mapped["Shop"] = relationship(back_populates="customers")
    primary_staff: Mapped["User | None"] = relationship()

    # Ensure unique mobile per shop (excluding archived)
    __table_args__ = (
        # Unique index on shop_id and mobile for non-archived customers
        # This allows reusing mobile numbers after a customer is archived
        # Created via migration: uq_customers_shop_id_mobile_active
        {"sqlite_autoincrement": True},
    )