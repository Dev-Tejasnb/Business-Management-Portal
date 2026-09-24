"""Shop / Tenant model.

A shop is a tenant in the SaaS. It stores the foundation fields required for
operation. The model is intentionally minimal now but is designed to be extended
in later phases (address, contact, branding, subscription, custom domain,
services, staff, settings) without breaking existing code.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Sequence, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

shop_code_seq = Sequence("shop_code_seq", metadata=Base.metadata)

if TYPE_CHECKING:
    from app.models.manager_assignment import PlatformManagerShop
    from app.models.membership import ShopMembership
    from app.models.service import Service
    from app.models.customer import Customer
    from app.models.application import Application


class ShopStatus(str, Enum):
    """Foundation lifecycle statuses for a shop/tenant."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Shop(TimestampMixin, Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ShopStatus.ACTIVE.value, nullable=False, index=True
    )

    memberships: Mapped[list["ShopMembership"]] = relationship(
        back_populates="shop",
        cascade="all, delete-orphan",
    )
    manager_assignments: Mapped[list["PlatformManagerShop"]] = relationship(
        back_populates="shop",
        cascade="all, delete-orphan",
    )
    services: Mapped[list["Service"]] = relationship(
        back_populates="shop",
        cascade="all, delete-orphan",
    )
    customers: Mapped[list["Customer"]] = relationship(
        back_populates="shop",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="shop",
        cascade="all, delete-orphan",
    )

    @property
    def status_enum(self) -> ShopStatus:
        return ShopStatus(self.status)