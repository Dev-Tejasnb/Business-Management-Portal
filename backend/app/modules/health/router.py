"""Health check routes.

- ``/api/v1/health`` — readiness: checks database, Redis and MinIO.
- Liveness at ``/health`` (see ``app/main.py``) — no dependencies.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from sqlalchemy import text

from app import __version__
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.minio import ping_minio
from app.core.redis import ping_redis
from app.modules.health.schemas import (
    DependencyHealth,
    HealthStatus,
    ReadinessResponse,
)

router = APIRouter()


async def _check_db() -> DependencyHealth:
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return DependencyHealth(name="database", ok=True)
    except Exception as exc:  # noqa: BLE001
        return DependencyHealth(name="database", ok=False, detail=str(exc))


async def _check_redis() -> DependencyHealth:
    ok = await ping_redis()
    return DependencyHealth(name="redis", ok=ok)


async def _check_minio() -> DependencyHealth:
    ok = await ping_minio()
    return DependencyHealth(name="minio", ok=ok)


@router.get("", response_model=ReadinessResponse, summary="Readiness check")
async def readiness() -> ReadinessResponse:
    """Report overall service health and each dependency's status."""
    db_result, redis_result, minio_result = await asyncio.gather(
        _check_db(), _check_redis(), _check_minio()
    )

    dependencies = [db_result, redis_result, minio_result]
    status = (
        HealthStatus.OK
        if all(dep.ok for dep in dependencies)
        else HealthStatus.DEGRADED
    )

    return ReadinessResponse(
        status=status,
        version=__version__,
        dependencies=dependencies,
    )