"""Document model.

Represents an uploaded document attached to an application.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.service_field import ServiceRequiredDocument
    from app.models.shop import Shop
    from app.models.user import User


class DocumentStatus(str, Enum):
    """Document lifecycle statuses."""

    UPLOADED = "uploaded"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Document(TimestampMixin, Base):
    """Document uploaded for an application in a shop."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_required_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, index=True
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default=DocumentStatus.UPLOADED.value,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    shop: Mapped["Shop"] = relationship()
    application: Mapped["Application"] = relationship(back_populates="documents")
    required_document: Mapped["ServiceRequiredDocument | None"] = relationship()
    uploader: Mapped["User"] = relationship(foreign_keys=[uploaded_by])
    verifier: Mapped["User | None"] = relationship(foreign_keys=[verified_by])

    # Constraints
    __table_args__ = (
        CheckConstraint(
            status.in_([
                DocumentStatus.UPLOADED.value,
                DocumentStatus.VERIFIED.value,
                DocumentStatus.REJECTED.value,
                DocumentStatus.ARCHIVED.value,
            ]),
            name="ck_document_status",
        ),
    )

    @property
    def status_enum(self) -> DocumentStatus:
        return DocumentStatus(self.status)
