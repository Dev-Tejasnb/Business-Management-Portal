"""Feature modules.

Each business module is added here as its own package (e.g. ``modules/shops/``,
``modules/auth/``) containing ``router.py`` and ``schemas.py``. The health module
serves as the canonical template for future modules.
"""

from app.modules.auth import router as auth_router
from app.modules.health import router as health_router

__all__ = ["auth_router", "health_router"]