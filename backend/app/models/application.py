"""Application model.

Represents an application for a service by a customer in a shop.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String, ForeignKey, Integer, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.customer import Customer
    from app.models.service import Service
    from app.models.user import User
    from app.models.document import Document


class ApplicationStatus(str, Enum):
    """Application lifecycle statuses."""

    ENQUIRY = "enquiry"
    APPLIED = "applied"
    DOCUMENTS_PENDING = "documents_pending"
    UNDER_PROCESSING = "under_processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Application(TimestampMixin, Base):
    """Application for a service by a customer in a shop."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    application_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    assigned_staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    application_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    shop: Mapped["Shop"] = relationship()
    customer: Mapped["Customer"] = relationship()
    service: Mapped["Service"] = relationship()
    assigned_staff: Mapped["User | None"] = relationship()
    documents: Mapped[list["Document"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            status.in_([
                ApplicationStatus.ENQUIRY.value,
                ApplicationStatus.APPLIED.value,
                ApplicationStatus.DOCUMENTS_PENDING.value,
                ApplicationStatus.UNDER_PROCESSING.value,
                ApplicationStatus.COMPLETED.value,
                ApplicationStatus.REJECTED.value,
                ApplicationStatus.CANCELLED.value,
            ]),
            name="ck_application_status",
        ),
    )

    @property
    def status_enum(self) -> ApplicationStatus:
        return ApplicationStatus(self.status)