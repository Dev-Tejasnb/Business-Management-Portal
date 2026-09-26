"""Customer authentication service.

Handles credential verification and the access/refresh token lifecycle for customer accounts.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    verify_password,
)
from app.core.session import SessionStore
from app.models.customer_account import CustomerAccount
from app.core.audit import audit_service, Module, AuditAction
from app.core.logging import get_logger

logger = get_logger(__name__)


class CustomerAuthService:
    """Verifies customer credentials and manages the token/session lifecycle."""

    async def authenticate(
        self, db: AsyncSession, email: str, password: str, shop_id: int
    ) -> CustomerAccount | None:
        """Return the customer account if credentials are valid and the account is active.

        Args:
            db: Database session
            email: Customer email (will be normalized to lowercase and stripped)
            password: Plaintext password
            shop_id: Shop ID for tenant isolation

        Returns:
            CustomerAccount if authentication successful, None otherwise
        """
        # Normalize email
        email_normalized = email.strip().lower()

        # Get customer account by email and shop_id (tenant isolation)
        stmt = (
            select(CustomerAccount)
            .where(
                CustomerAccount.email == email_normalized,
                CustomerAccount.shop_id == shop_id,
            )
        )
        result = await db.execute(stmt)
        customer_account = result.scalar_one_or_none()

        if customer_account is None:
            # Log failed login attempt (audit)
            await audit_service.record(
                action=AuditAction.LOGIN_FAILURE,
                module=Module.CUSTOMER,
                actor_user_id=None,  # No user yet
                actor_role="CUSTOMER",
                shop_id=shop_id,
                entity_type="customer_account",
                entity_id=None,  # Unknown
                old_values=None,
                new_values={"email": email_normalized, "reason": "invalid_credentials"},
                ip_address=None,  # Will be filled by router if available
                user_agent=None,
            )
            return None

        # Check account status
        if customer_account.status != "active":
            await audit_service.record(
                action=AuditAction.LOGIN_FAILURE,
                module=Module.CUSTOMER,
                actor_user_id=None,
                actor_role="CUSTOMER",
                shop_id=shop_id,
                entity_type="customer_account",
                entity_id=str(customer_account.id),
                old_values=None,
                new_values={"email": email_normalized, "reason": f"account_{customer_account.status}"},
                ip_address=None,
                user_agent=None,
            )
            return None

        # Verify password
        if not verify_password(password, customer_account.hashed_password):
            # Increment failed login attempts
            customer_account.failed_login_attempts += 1

            # Lock account if too many failed attempts (e.g., 5)
            if customer_account.failed_login_attempts >= 5:
                from datetime import datetime, timedelta
                customer_account.locked_until = datetime.now() + timedelta(minutes=30)

            await db.flush()

            await audit_service.record(
                action=AuditAction.LOGIN_FAILURE,
                module=Module.CUSTOMER,
                actor_user_id=None,
                actor_role="CUSTOMER",
                shop_id=shop_id,
                entity_type="customer_account",
                entity_id=str(customer_account.id),
                old_values=None,
                new_values={
                    "email": email_normalized,
                    "failed_login_attempts": customer_account.failed_login_attempts,
                    "locked_until": customer_account.locked_until.isoformat() if customer_account.locked_until else None,
                    "reason": "invalid_password",
                },
                ip_address=None,
                user_agent=None,
            )
            return None

        # Reset failed login attempts on successful login
        if customer_account.failed_login_attempts > 0:
            customer_account.failed_login_attempts = 0
            customer_account.locked_until = None

        # Update last login time
        from datetime import datetime, timezone
        customer_account.last_login_at = datetime.now(timezone.utc)

        await db.flush()

        # Audit successful login
        await audit_service.record(
            action=AuditAction.LOGIN_SUCCESS,
            module=Module.CUSTOMER,
            actor_user_id=None,  # Will be set after we have the account
            actor_role="CUSTOMER",
            shop_id=shop_id,
            entity_type="customer_account",
            entity_id=str(customer_account.id),
            old_values=None,
            new_values={
                "email": email_normalized,
                "last_login_at": customer_account.last_login_at.isoformat(),
            },
            ip_address=None,
            user_agent=None,
        )

        return customer_account

    async def issue_tokens(
        self, store: SessionStore, customer_account: CustomerAccount
    ) -> tuple[str, str, int]:
        """Create an access token and a new refresh session.

        Returns (access_token, refresh_token, refresh_ttl_seconds).
        """
        access_token = create_access_token(subject=str(customer_account.id))
        refresh_token, ttl = await store.create(customer_account.id)
        return access_token, refresh_token, ttl

    async def rotate_session(
        self, store: SessionStore, refresh_token: str
    ) -> tuple[str, str, int, int] | None:
        """Rotate a refresh session: revoke the old token and issue a new pair.

        Returns (access_token, new_refresh_token, ttl, customer_account_id) or None if the
        token is invalid/expired/revoked.
        """
        customer_account_id = await store.validate(refresh_token)
        if customer_account_id is None:
            return None

        # Validate the customer account still exists and is active
        # Note: We don't have the db session here, so we'll rely on the router to validate
        # after getting the customer account from the token.
        await store.revoke(refresh_token)
        new_refresh, ttl = await store.create(customer_account_id)
        access_token = create_access_token(subject=str(customer_account_id))
        return access_token, new_refresh, ttl, customer_account_id

    async def revoke_session(self, store: SessionStore, refresh_token: str) -> bool:
        """Revoke a refresh session (logout)."""
        return await store.revoke(refresh_token)

    @staticmethod
    def refresh_ttl_seconds() -> int:
        from app.core.security import refresh_token_ttl_seconds
        return refresh_token_ttl_seconds()


customer_auth_service = CustomerAuthService()