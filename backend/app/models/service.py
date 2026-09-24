"""Service model.

Represents a service offered by a shop.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.service_category import ServiceCategory
    from app.models.service_required_document import ServiceRequiredDocument
    from app.models.service_field import ServiceField


class ServiceStatus(str, Enum):
    """Service lifecycle statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Service(TimestampMixin, Base):
    """Service offered by a shop."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    estimated_processing_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=ServiceStatus.ACTIVE.value, nullable=False, index=True
    )

    # Relationships
    shop: Mapped["Shop"] = relationship(back_populates="services")
    category: Mapped["ServiceCategory | None"] = relationship(back_populates="services")
    required_documents: Mapped[list["ServiceRequiredDocument"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
    fields: Mapped[list["ServiceField"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )

    @property
    def status_enum(self) -> ServiceStatus:
        return ServiceStatus(self.status)