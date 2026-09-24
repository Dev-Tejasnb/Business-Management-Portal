"""Service category model.

Represents a categorization for services offered by shops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.service import Service


class ServiceCategory(TimestampMixin, Base):
    """Category for grouping services."""

    __tablename__ = "service_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    services: Mapped[list["Service"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<ServiceCategory id={self.id} name={self.name}>"