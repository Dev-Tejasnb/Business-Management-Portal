"""Central tenant-context resolution.

This module is the single place that defines the active tenant (``shop_id``)
identity. Per the security rules, the tenant is derived ONLY from authenticated
membership context and/or the request hostname — never from a ``shop_id``
supplied by the frontend.

The actual async lookup (verifying an active membership for the current user)
lives in the auth/shops dependencies, which build a ``TenantContext`` from a
server-verified ``ShopMembership``. All future modules must use these helpers
rather than re-implementing tenant resolution.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import TenantIsolationError


@dataclass(frozen=True)
class TenantContext:
    """Immutable resolved tenant identity for the current request."""

    shop_id: int
    #: Server-verified shop-scope role of the caller within this tenant.
    shop_role: str | None = None
    # Future: hostname / slug / custom domain that helped resolve the tenant.
    hostname: str | None = None

    def enforce_scope(self, owner_shop_id: int) -> None:
        """Central guard used by repositories to prevent cross-tenant access.

        Called with the owning ``shop_id`` of any tenant-owned record. If the
        caller does not belong to that shop, raises a tenant-isolation error.
        """
        if owner_shop_id != self.shop_id:
            raise TenantIsolationError(
                detail={"shop_id": self.shop_id, "resource_owner": owner_shop_id}
            )


def build_tenant_context(
    *, shop_id: int, shop_role: str | None = None, hostname: str | None = None
) -> TenantContext:
    """Construct a tenant context from server-verified values."""
    return TenantContext(shop_id=shop_id, shop_role=shop_role, hostname=hostname)