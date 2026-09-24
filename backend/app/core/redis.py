"""Async Redis client management."""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None


def init_redis() -> Redis:
    """Create (or return) the shared async Redis client."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = Redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            encoding="utf-8",
        )
    return _redis


def get_redis() -> Redis:
    return init_redis()


async def close_redis() -> None:
    """Close the shared Redis connection pool."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def ping_redis() -> bool:
    """Return True if Redis responds to PING."""
    try:
        return bool(await get_redis().ping())
    except Exception:
        logger.warning("Redis connectivity check failed.")
        return False