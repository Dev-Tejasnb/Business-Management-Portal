"""SQLAlchemy declarative base and reusable mixins.

`Base` is the single declarative base used by all models. `TimestampMixin`
provides standard audit timestamps. `TenantScopedBase` prepares the multi-tenant
requirement: tenant-owned tables can inherit it to gain a `shop_id` column and a
central row-level filter hook used for isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func, types
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models in the application."""


class UUIDMixin:
    """Provides a UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Provides created_at / updated_at timestamps with DB defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantScopedBase:
    """Mixin for tenant-owned tables.

    Adds ``shop_id`` so every tenant-owned record is isolated. Enforcement is
    centralized (see ``app.core.tenant.TenantContext.enforce_scope``); modules
    must never trust a ``shop_id`` from the client.
    """

    shop_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )