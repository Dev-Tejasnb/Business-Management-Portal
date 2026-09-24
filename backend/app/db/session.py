"""Session dependency re-export."""

from app.core.database import get_db_session

__all__ = ["get_db_session"]