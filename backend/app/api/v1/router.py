"""Version 1 API router.

New feature modules are registered here as they are added in later phases. Keep
each module's routes under `app/modules/<name>/router.py`.
"""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.billing.router import router as billing_router
from app.modules.health.router import router as health_router
from app.modules.platform.shops.router import router as platform_shops_router
from app.modules.services.router import router as services_router
from app.modules.customers.router import router as customers_router
from app.modules.shops.router import router as shops_router
from app.modules.staff.router import router as staff_router
from app.modules.applications.router import router as applications_router
from app.modules.documents.router import router as documents_router
from app.modules.reports.router import router as reports_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(shops_router, tags=["shops"])
api_router.include_router(platform_shops_router, tags=["platform-shops"])
api_router.include_router(staff_router, tags=["staff"])
api_router.include_router(services_router, tags=["services"])
api_router.include_router(customers_router, tags=["customers"])
api_router.include_router(applications_router, tags=["applications"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(billing_router, tags=["billing"])
api_router.include_router(reports_router, tags=["reports"])