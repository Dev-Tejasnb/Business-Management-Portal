"""Development bootstrap for the initial Platform Owner.

This is an explicit, deliberate command — it is NOT run automatically at
application startup, and it will never create an account with a hardcoded
password. Credentials come from environment variables.

Usage:
    docker compose exec backend python -m app.scripts.bootstrap_platform_owner

Required environment variables (see .env):
    BOOTSTRAP_PLATFORM_OWNER_EMAIL
    BOOTSTRAP_PLATFORM_OWNER_PASSWORD
    BOOTSTRAP_PLATFORM_OWNER_NAME

The command is idempotent: if a user with the given email already exists, it
refuses to overwrite it. In production this must be run deliberately by an
administrator (ideally with a generated one-time password that is then rotated).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.audit import AuditAction, Module, audit_service
from app.core.config import get_settings
from app.core.database import dispose_engine, get_session_factory, init_engine
from app.core.roles import PlatformRole
from app.core.security import hash_password
from app.models.user import User


async def _bootstrap() -> None:
    settings = get_settings()

    email = settings.BOOTSTRAP_PLATFORM_OWNER_EMAIL.strip().lower()
    password = settings.BOOTSTRAP_PLATFORM_OWNER_PASSWORD
    name = settings.BOOTSTRAP_PLATFORM_OWNER_NAME.strip()

    missing = [
        label
        for label, value in (
            ("BOOTSTRAP_PLATFORM_OWNER_EMAIL", email),
            ("BOOTSTRAP_PLATFORM_OWNER_PASSWORD", password),
            ("BOOTSTRAP_PLATFORM_OWNER_NAME", name),
        )
        if not value
    ]
    if missing:
        raise SystemExit(
            "Missing bootstrap environment variables: " + ", ".join(missing)
            + "\nSet them in .env before running this command."
        )
    if not email or "@" not in email:
        raise SystemExit("BOOTSTRAP_PLATFORM_OWNER_EMAIL must be a valid email.")

    init_engine()
    factory = get_session_factory()

    async with factory() as db:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"Platform owner already exists for {email}; skipping (no changes).")
            return

        user = User(
            email=email,
            full_name=name,
            hashed_password=hash_password(password),
            platform_role=PlatformRole.OWNER.value,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.commit()  # Commit user first so audit FK succeeds

        await audit_service.record(
            action=AuditAction.ACCOUNT_ACTIVATED,
            module=Module.USER,
            actor_user_id=user.id,
            actor_role=user.platform_role,
            entity_type="user",
            entity_id=str(user.id),
            new_values={"email": email, "platform_role": user.platform_role},
        )
        print(f"Created platform owner: {email} (role={user.platform_role}).")

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(_bootstrap())