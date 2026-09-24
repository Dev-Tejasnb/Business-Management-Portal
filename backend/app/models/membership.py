"""Shop membership model.

Links a user to a shop with a shop-scope role and an active/inactive state.
A user may hold multiple memberships (one per shop); a unique constraint on
(user_id, shop_id) prevents duplicate membership in the same shop. Platform
users do not require a membership to operate at platform scope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.roles import ShopRole
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.user import User


class ShopMembership(TimestampMixin, Base):
    __tablename__ = "shop_memberships"
    __table_args__ = (UniqueConstraint("user_id", "shop_id", name="uq_membership_user_shop"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="memberships")
    shop: Mapped["Shop"] = relationship(back_populates="memberships")

    @property
    def role_enum(self) -> ShopRole:
        return ShopRole(self.role)