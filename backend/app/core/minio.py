"""MinIO (S3-compatible) object storage client.

Provides a shared client and helpers to verify connectivity and ensure the
private documents bucket exists. Document management is NOT implemented in
Phase 1; this only prepares the storage foundation.
"""

from __future__ import annotations

from minio import Minio

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: Minio | None = None


def init_minio() -> Minio:
    """Create (or return) the shared MinIO client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


def get_minio() -> Minio:
    return init_minio()


async def ensure_bucket() -> None:
    """Create the configured bucket if it does not exist, as private.

    Note: Minio client methods are synchronous; this helper is async so callers
    can await it uniformly, but work runs in the caller's threadpool via
    run_in_executor when used from an endpoint.
    """
    settings = get_settings()
    client = get_minio()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)
        logger.info("Created MinIO bucket '%s'.", settings.MINIO_BUCKET)


async def ping_minio() -> bool:
    """Return True if MinIO responds and the bucket is reachable."""
    try:
        client = get_minio()
        return client.bucket_exists(get_settings().MINIO_BUCKET)
    except Exception:
        logger.warning("MinIO connectivity check failed.")
        return False