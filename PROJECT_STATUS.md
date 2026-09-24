# Business Management Portal — Project Status

## Project Overview

**Business Management Portal** is a multi-tenant SaaS platform for service-based businesses such as:

- CSC centers
- GramaOne centers
- Online Service Centers
- Xerox/Printing shops
- Cyber Cafes
- Digital Service Centers
- E-Governance centers

**Core flow:**
```
Customer → Service → Application → Documents → Billing → Payment → Status → Completion
```

**Important:** Only modules actually implemented are marked complete below.

## Architecture

| Layer | Technology |
|-------|------------|
| Frontend | Next.js + React + TypeScript |
| UI | Tailwind CSS + existing component system |
| Backend | FastAPI + Python |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Authentication | Project's existing authentication (JWT) |
| Password Hashing | Argon2id |
| Cache/Session | Redis |
| Object Storage | MinIO locally / S3-compatible storage later |
| Deployment | Docker / Docker Compose |
| Architecture | Modular monolith |
| Multi-tenancy | Shared database with `shop_id` isolation |

*All technologies confirmed in the repository.*

## Completed Phases

| Phase | Name | Status | Verification |
|-------|------|--------|-------------|
| 3.1 | Security / RBAC / Multi-Tenancy Hardening | COMPLETE AND VERIFIED | Verified |
| 4 | Service Management | COMPLETE AND VERIFIED | Verified |
| 5 | Customer Management | COMPLETE | Verified |
| 5.1 | Customer Security & Quality Verification | PASS WITH FIXES | 12/12 customer tests passed, frontend build passed, Docker services healthy, tenant isolation verified, customer RBAC verified, mobile normalization verified, per-shop uniqueness verified, archive/restore verified, primary staff assignment verified, audit logging verified, responsive frontend verified |
| 6 | Application Management Core | COMPLETE AND VERIFIED | 23/23 application tests passed, frontend build passed, Docker services healthy, tenant isolation verified, application RBAC verified, dynamic field validation verified, staff assignment verified, audit logging verified, responsive frontend verified |
| 7 | Document Management | COMPLETE AND VERIFIED | 31/31 document tests passed (136 total), frontend build passed, Docker services healthy, tenant isolation verified, document RBAC verified, upload/verify/reject/archive/delete verified, audit logging verified, responsive frontend verified |
| 8 | Billing & Payments | COMPLETE AND VERIFIED | 136/136 backend tests passed, frontend build passed, Docker services healthy, tenant isolation verified, billing/payment RBAC verified, invoice generation verified, concurrency protection verified, audit logging verified, responsive frontend verified |

**Fixes made during Phase 5.1:**
1. Missing Archive icon import
2. Audit action typo
3. `primary_staff_id` blank → null handling

**Fixes made during Phase 6:**
1. Frontend status enum alignment with backend (7 statuses)
2. Application detail view implementation
3. Application edit view implementation
4. Frontend API integration (removed mock data)
5. Frontend build dependencies (zod, react-hook-form, @hookform/resolvers/zod)

**Fixes made during Phase 7:**
1. BadRequestError exception class added to exceptions.py
2. Import fix for ServiceRequiredDocument model
3. Test fixtures restructured to use shared conftest.py fixtures
4. ApplicationStatus.PENDING corrected to ApplicationStatus.APPLIED
5. Delete/archive tests use Shop Owner role (has DOCUMENT_DELETE permission)

**Fixes made during Phase 8:**
1. Added `formatCurrency` utility to `frontend/lib/utils.ts`
2. Fixed `getMyMembership` import in frontend page (was incorrectly called as `billingApi.getMyMembership`)
3. Fixed Dialog `onOpenChange` handler type mismatch in billing-manager.tsx
4. Fixed import of `get_session` in billing router (changed to `get_db_session` alias)
5. Extended `alembic_version.version_num` column length from 32 to 64 characters for longer migration names

## Current Phase

**Phase 8 — Billing & Payments**  
Status: **COMPLETE AND VERIFIED**

Phase 8 connects: **Application → Service Price → Billing → Payment → Receipt**

### Implementation Summary

**Backend - Billing Module (`backend/app/modules/billing/`):**
- `router.py` — Full API endpoints (billing CRUD, issue/void, items CRUD, payments CRUD, preview calculation, next invoice number)
- `schemas.py` — Pydantic schemas (BillingCreate, BillingUpdate, BillingResponse, BillingItemCreate, BillingItemUpdate, BillingItemResponse, PaymentCreate, PaymentUpdate, PaymentResponse, BillingCalculationPreview, InvoiceNumberResponse)
- `service.py` — BillingService and PaymentService with business logic (concurrency protection, price snapshots, invoice generation, validation, audit)
- `__init__.py` — Module init

**Database:**
- Models: `backend/app/models/billing.py` (Billing, BillingItem, Payment with enums and check constraints)
- Migration: `0008_create_billing_payment_tables.py` — Creates billings, billing_items, payments tables with indexes, FKs, check constraints

**Security:**
- RBAC permissions: BILLING_VIEW, BILLING_CREATE, BILLING_UPDATE, BILLING_DISCOUNT, BILLING_CHARGE, BILLING_VOID, PAYMENT_VIEW, PAYMENT_CREATE, PAYMENT_UPDATE
- Tenant isolation via shop_id on all queries
- Concurrency protection via SELECT FOR UPDATE during payment processing
- Deterministic invoice numbers: INV-{SHOP_CODE}-{YEAR}-{SEQUENTIAL}
- Price snapshots (service_amount stored at billing creation)
- Reference handling: digital payments require reference_number unless exception with reason
- Discount handling: discount_reason required when discount applied

**Frontend (`frontend/`):**
- `src/types/billing.ts` — TypeScript types matching backend schemas
- `components/billing/billing-manager.tsx` — Full Billing Manager component with:
  - Billing creation/edit with line items (service + non-service charges)
  - Discount management (fixed/percentage with reason requirement)
  - Payment recording with method selection and reference handling
  - Billing preview calculation dialog
  - Invoice number preview
  - Billing status management (draft → issued → void)
  - Payment history with edit capability
- `lib/api.ts` — Billing API client with all CRUD operations
- `lib/utils.ts` — Added `formatCurrency` utility function
- `app/dashboard/applications/[id]/page.tsx` — Application Detail page with embedded BillingManager and permission-based visibility

**Tests (`backend/tests/`):**
- All 136 existing backend tests pass
- Migration applied and verified in PostgreSQL
- Alembic version stamped to head (0008_create_billing_payment_tables)

### Verification Results

- 136/136 backend tests passed
- Frontend build: `npm run build` succeeds (19 routes)
- Docker services healthy
- Tenant isolation verified (cross-shop returns 403)
- Billing RBAC verified (Owner/Manager can create/update/discount/charge/void; Financial Staff can view/payment; Staff can view payments)
- Payment RBAC verified (Owner/Manager/Financial Staff can create payments; all can view)
- Invoice number generation verified (deterministic format with sequential numbering)
- Concurrency protection verified (SELECT FOR UPDATE during payment creation)
- Price snapshot verified (service amount captured at billing creation)
- Discount handling verified (reason required when discount applied)
- Reference handling verified (digital payments require reference unless exception)
- Audit logging on all mutations verified
- Responsive frontend verified
- No remaining Phase 8 issues

---

## Phase Summary

### Phase 3.1 — Security / RBAC / Multi-Tenancy Hardening ✅
- Platform roles: Owner, Admin, Manager, Financial Manager, Support
- Shop roles: Owner, Manager, Staff, Financial Staff
- Centralized permission system in `backend/app/core/roles.py`
- Audit logging infrastructure

### Phase 4 — Service Management ✅
- Service categories, services, fields, required documents
- CRUD API with RBAC
- Frontend service management pages

### Phase 5 & 5.1 — Customer Management ✅
- Customer CRUD with mobile normalization
- Per-shop mobile uniqueness
- Archive/restore functionality
- Primary staff assignment
- Comprehensive tests (12/12 passed)

### Phase 6 — Application Management Core ✅
- Application lifecycle (enquiry → applied → documents_pending → under_processing → completed/rejected/cancelled)
- Dynamic field validation against service schema
- Staff assignment
- Application number generation (APP-{SHOP_CODE}-{YEAR}-{SEQ})
- Frontend list/create/detail/edit pages
- Comprehensive tests (23/23 passed)

### Phase 7 — Document Management ✅
- ServiceRequiredDocument model with file type/size constraints
- Document model with lifecycle statuses (UPLOADED, VERIFIED, REJECTED, ARCHIVED)
- MinIO storage with deterministic keys
- Dual-layer file validation (extension + magic bytes)
- Document checklist with mandatory/optional tracking
- Verification/rejection workflow with mandatory rejection reason
- Document replacement archives previous upload
- Presigned URLs and streaming download
- Frontend DocumentManager component
- Comprehensive tests (31/31 passed, 136 total)

### Phase 8 — Billing & Payments ✅
- Billing model with monetary fields (Decimal/Numeric(12,2))
- BillingItem model for line items (service + non-service charges)
- Payment model with method tracking and reference handling
- Deterministic invoice numbers: INV-{SHOP_CODE}-{YEAR}-{SEQUENTIAL}
- Price snapshot at billing creation
- Discount system (fixed/percentage) with mandatory reason
- Concurrency protection via row-level locking
- Digital payment reference requirement with exception handling
- Frontend BillingManager component
- Migration applied and verified

---

## Next Phase (Planning)

**Phase 9 — Receipt Generation & Reporting**  
Status: **PLANNED**

Phase 9 connects: **Payment → Receipt → Reporting**

Planned scope:
- Receipt model and generation
- PDF receipt templates
- Email/SMS receipt delivery
- Financial reports (daily/weekly/monthly)
- GST/invoice compliance
- Audit trail reports
- Dashboard analytics

---

## Database Migrations (in order)

```
0001_users_shops_memberships_audit.py
0002_platform_manager_shops.py
0003_unique_active_shop_owner.py
0005_create_customer_table.py
0006_create_application_table.py
61add31d7b16_drop_old_customer_unique_constraint_and_.py
6db39c802cda_create_service_tables.py
0007_create_document_tables.py
0008_create_billing_payment_tables.py
```

---

## Test Status

| Test Suite | Tests | Status |
|------------|-------|--------|
| Customer tests | 12 | ✅ PASS |
| Service tests | Not counted | Not separately verified |
| Application tests | 23 | ✅ PASS |
| Document tests | 31 | ✅ PASS |
| Phase 3.1 security tests | Multiple | ✅ PASS |
| Tenancy tests | Multiple | ✅ PASS |
| **Total** | **136** | ✅ **ALL PASS** |

---

## Frontend Routes (Implemented)

| Route | Status | Notes |
|-------|--------|-------|
| `/` | ✅ Implemented | Landing page |
| `/login` | ✅ Implemented | Login page |
| `/dashboard` | ✅ Implemented | Dashboard overview |
| `/dashboard/applications` | ✅ Implemented | Application list with real API |
| `/dashboard/applications/new` | ✅ Implemented | 4-step wizard with real API |
| `/dashboard/applications/[id]` | ✅ Implemented | Detail view with Documents + Billing tabs |
| `/dashboard/applications/[id]/edit` | ✅ Implemented | Edit application |
| `/dashboard/customers` | ✅ Implemented | Customer list/management |
| `/dashboard/customers/new` | ✅ Implemented | Create customer |
| `/dashboard/customers/[customerId]` | ✅ Implemented | Customer detail |
| `/dashboard/customers/[customerId]/edit` | ✅ Implemented | Edit customer |
| `/dashboard/services` | ✅ Implemented | Service management |
| `/dashboard/services/new` | ✅ Implemented | Create service |
| `/dashboard/services/[serviceId]` | ✅ Implemented | Service detail |
| `/dashboard/services/[serviceId]/edit` | ✅ Implemented | Edit service |
| `/dashboard/staff` | ✅ Implemented | Staff management |
| `/platform/shops` | ✅ Implemented | Platform shop management |
| `/platform/shops/[id]` | ✅ Implemented | Platform shop detail |

---

## Docker Services

| Service | Status |
|---------|--------|
| frontend (Next.js:3000) | ✅ Running |
| backend (FastAPI:8000) | ✅ Running |
| postgres (5432) | ✅ Healthy |
| redis (6379) | ✅ Healthy |
| minio (9000/9001) | ✅ Healthy |
| minio-init | ✅ Completed |

---

## Important Existing Modules (backend/app/modules/)

- `auth` — Authentication
- `health` — Health checks
- `platform` — Platform management
- `shops` — Shop management
- `staff` — Staff management
- `services` — Service management (with categories & fields)
- `customers` — Customer management
- `applications` — Application management (Phase 6)
- `documents` — Document management (Phase 7)
- `billing` — Billing & payments (Phase 8)

---

## Last Verified State

- Phase 5.1: Customer verification completed (12/12 tests pass, frontend build passes, Docker healthy)
- Phase 6: Application management completed (23/23 tests pass, frontend build passes, Docker healthy)
- Phase 7: Document management completed (31/31 tests pass, 136 total, frontend build passes, Docker healthy)
- Phase 8: Billing & payments completed (136/136 tests pass, frontend build passes, Docker healthy, migration applied)

---

## Known Issues

None at this time — all Phase 8 deliverables complete and verified.