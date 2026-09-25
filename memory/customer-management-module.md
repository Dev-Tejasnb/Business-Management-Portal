---
name: customer-management-module
description: Implemented Phase 5 Customer Management module with shop-scoped customers, phone normalization, RBAC, audit logging, and soft-delete/archive functionality
metadata:
  type: project
---

Completed implementation of Customer Management module (Phase 5) for the Business Management Portal.

## Key Features Implemented

1. **Shop-Scoped Customer Isolation**: Every customer is tied to a specific shop via `shop_id` foreign key
2. **Phone Number Normalization**: Created utility that standardizes Indian phone numbers to `+91XXXXXXXXXX` format
3. **Composite Unique Constraint**: Enforced uniqueness of `(shop_id, mobile)` pair allowing same mobile across different shops
4. **RBAC Permissions**: Added `CUSTOMER_VIEW`, `CUSTOMER_CREATE`, `CUSTOMER_UPDATE`, `CUSTOMER_ARCHIVE` permissions mapped to shop roles
5. **Soft Delete / Archive**: Customers can be archived (`status="archived"`) and restored, preserving historical data
6. **Audit Logging**: All customer mutations logged via `AuditService` with `Module.CUSTOMER` and old/new value tracking
7. **Primary Staff Assignment**: Staff assignment with validation ensuring staff belongs to same shop
8. **REST API Endpoints**: Full CRUD operations with proper validation and error handling
9. **Frontend UI**: Complete customer management interface under `/dashboard/customers` with list, detail, create, and edit views

## Files Created/Modified

### Backend
- `backend/app/models/customer.py` - Customer model with shop_id, mobile, primary_staff_id, status
- `backend/app/models/__init__.py` - Exported Customer and CustomerStatus
- `backend/app/models/shop.py` - Added customers relationship
- `backend/alembic/versions/0005_create_customer_table.py` - Migration creating customers table with indexes and unique constraint
- `backend/app/core/roles.py` - Added CUSTOMER_* permissions and mapped to shop roles
- `backend/app/core/audit.py` - Added CUSTOMER to Module enum
- `backend/app/modules/customers/schemas.py` - Pydantic v2 schemas for customer operations
- `backend/app/modules/customers/service.py` - Business logic with phone normalization, duplicate checks, staff validation
- `backend/app/modules/customers/router.py` - REST endpoints with RBAC and audit logging
- `backend/app/modules/customers/__init__.py` - Module initialization
- `backend/app/api/v1/router.py` - Registered customer router
- `backend/tests/test_customers.py` - Comprehensive test suite

### Frontend
- `frontend/app/dashboard/customers/page.tsx` - Customer list with search, filtering, pagination
- `frontend/app/dashboard/customers/new/page.tsx` - Create customer form
- `frontend/app/dashboard/customers/[customerId]/page.tsx` - Customer detail view
- `frontend/app/dashboard/customers/[customerId]/edit/page.tsx` - Edit customer form

## Technical Details

### Phone Normalization
- Strips all non-digit characters except leading '+'
- Converts 10-digit numbers to `+91XXXXXXXXXX` format
- Handles numbers with 91 prefix correctly
- Preserves '+' for international format

### Database Schema
- `customers` table with columns: id, shop_id (FK), name, mobile, email, address, notes, status, primary_staff_id (FK)
- Indexes on shop_id, mobile, status
- Unique constraint on (shop_id, mobile)

### Status Values
- `ACTIVE` - Normal customer
- `INACTIVE` - Temporarily inactive
- `ARCHIVED` - Soft deleted (can be restored)

### Permissions Mapping
- Shop Owner: All customer permissions
- Shop Manager: VIEW, CREATE, UPDATE, ARCHIVE
- Staff: VIEW, CREATE, UPDATE
- Financial Staff: VIEW only

### Audit Actions
- `customer.created` - On creation
- `customer.updated` - On modification
- `customer.archived` - On archiving
- `customer.restored` - On restoration
- Includes old_values, new_values, actor_role, shop_id

## Verification
- All backend tests pass
- Frontend builds successfully
- Routes accessible and functional
- Phone normalization working correctly
- Duplicate prevention enforced per shop
- Staff validation ensures same-shop assignment
- Archive/restore functionality tested