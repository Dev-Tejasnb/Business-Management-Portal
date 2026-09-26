"""FastAPI application entrypoint.

Wires configuration, logging, CORS, exception handlers, lifespan-managed
clients (DB, Redis, MinIO) and the versioned API router.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import dispose_engine, init_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, init_logging
from app.core.minio import ensure_bucket, init_minio
from app.core.redis import close_redis, init_redis
from app.modules.health.schemas import HealthStatus, LivenessResponse

logger = get_logger(__name__)

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise and tear down shared resources."""
    init_logging(settings)
    logger.info("Starting %s v%s (env=%s)", settings.APP_NAME, __version__, settings.APP_ENV)

    init_engine()
    init_redis()
    init_minio()

    try:
        await ensure_bucket()
    except Exception:  # noqa: BLE001
        # Storage availability should not prevent the API from serving /health.
        logger.warning("Could not ensure MinIO bucket at startup: %s", exc_info=True)

    yield

    await close_redis()
    await dispose_engine()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        debug=settings.APP_DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", response_model=LivenessResponse, tags=["health"], summary="Liveness check")
    async def liveness() -> LivenessResponse:
        """No-dependency liveness probe used by orchestrators/load balancers."""
        return LivenessResponse(status=HealthStatus.OK, app=settings.APP_NAME, version=__version__)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"app": settings.APP_NAME, "status": "running", "version": __version__}

    return app


app = create_app()