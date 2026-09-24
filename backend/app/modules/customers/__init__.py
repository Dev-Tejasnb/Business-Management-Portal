"""Customer Management Module.

Provides shop-scoped customer management including:
- Customer CRUD operations with phone normalization
- Duplicate mobile detection per shop
- Primary staff assignment with same-shop validation
- Soft delete (archive) and restore functionality
- Audit logging for all mutations
"""

from app.modules.customers import service
from app.modules.customers import schemas

__all__ = ["service", "schemas"]