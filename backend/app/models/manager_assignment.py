"""Platform Manager shop assignment model.

Links Platform Managers to shops they are authorized to manage. A Platform Manager
can only access shops they are explicitly assigned to (and where the assignment
is active). Platform Owners/Admins can manage shops without assignment.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PlatformManagerShop(TimestampMixin, Base):
    __tablename__ = "platform_manager_shops"
    __table_args__ = (
        UniqueConstraint("user_id", "shop_id", name="uq_manager_shop_assignment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="managed_shops")
    shop: Mapped["Shop"] = relationship(back_populates="manager_assignments")