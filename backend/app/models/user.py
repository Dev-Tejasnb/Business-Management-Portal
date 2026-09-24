"""User model.

A user has a unique platform-level identity. Shop affiliation is expressed
through ``ShopMembership`` records so a user can belong to multiple shops in the
future. A user's platform role (``platform_role``) is optional; users without one
operate purely at shop scope through memberships.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.roles import PlatformRole
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.manager_assignment import PlatformManagerShop
    from app.models.membership import ShopMembership


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # Platform role is optional (None = shop-only user).
    platform_role: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    memberships: Mapped[list["ShopMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    managed_shops: Mapped[list["PlatformManagerShop"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def platform_role_enum(self) -> PlatformRole | None:
        return PlatformRole(self.platform_role) if self.platform_role else None