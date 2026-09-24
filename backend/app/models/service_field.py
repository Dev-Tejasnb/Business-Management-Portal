"""Service required document and form field models.

Represents requirements and intake fields configured for services.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.service import Service


class FieldType(str, Enum):
    """Field types supported in service dynamic intake forms."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    TEXTAREA = "textarea"
    BOOLEAN = "boolean"


class ServiceRequiredDocument(TimestampMixin, Base):
    """Required document specification for a service."""

    __tablename__ = "service_required_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_file_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    max_file_size_mb: Mapped[int | None] = mapped_column(Integer, default=10, nullable=True)

    # Relationships
    service: Mapped["Service"] = relationship(back_populates="required_documents")

    def __repr__(self) -> str:
        return f"<ServiceRequiredDocument id={self.id} service_id={self.service_id} name={self.name}>"


class ServiceField(TimestampMixin, Base):
    """Custom intake form field specification for a service."""

    __tablename__ = "service_fields"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(
        String(50), default=FieldType.TEXT.value, nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    validation_rules: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    service: Mapped["Service"] = relationship(back_populates="fields")

    @property
    def field_type_enum(self) -> FieldType:
        return FieldType(self.field_type)

    def __repr__(self) -> str:
        return f"<ServiceField id={self.id} service_id={self.service_id} name={self.name} field_type={self.field_type}>"