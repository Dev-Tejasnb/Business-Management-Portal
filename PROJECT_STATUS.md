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
| 9 | Reports & Financial Analytics | COMPLETE AND VERIFIED | 28/28 report tests passed, frontend build passed, Docker services healthy, tenant isolation verified, report RBAC verified, Decimal precision verified, export functionality verified |

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

**Fixes made during Phase 9:**
1. Fixed `KeyError: 'methods'` in payment method analytics by mapping `by_method` to `methods` in service layer
2. Fixed `KeyError: 'group_by'` in application report by adding `group_by` to return payload
3. Fixed `AttributeError: 'Application' has no attribute 'created_by'` by filtering on `assigned_staff_id`
4. Fixed test fixture isolation issues (13 tests) by explicitly injecting `sample_user_owner`, `sample_application`, `sample_billing`, `sample_payment`, `sample_document` fixtures due to pytest-asyncio TRUNCATE TABLE behavior
5. Fixed `NotNullViolationError` in document analytics test by setting `uploaded_by` field
6. Installed missing frontend dependencies: `date-fns`, `recharts`, `@radix-ui/react-switch`

## Current Phase

**Phase 9 — Reports & Financial Analytics**  
Status: **COMPLETE AND VERIFIED**

### Implementation Summary

**Backend - Reports Module (`backend/app/modules/reports/`):**
- `router.py` — 13 JSON report endpoints and 13 CSV export endpoints with `REPORT_VIEW` and `REPORT_EXPORT` RBAC enforcement and shop isolation.
- `schemas.py` — Pydantic schemas for all report endpoints and date filters.
- `service.py` — ReportsService implementing aggregation logic using Decimal arithmetic and SQLAlchemy date and aggregate functions.
- `__init__.py` — Module init

**Security & Isolation:**
- RBAC permissions: `REPORT_VIEW` (Owner, Manager, Financial Staff) and `REPORT_EXPORT` (Owner, Manager).
- Strict multi-tenant isolation on every report and CSV export query via `shop_id`.
- Decimal / `Numeric(12,2)` precision for all financial calculations.

**Frontend (`frontend/`):**
- `app/dashboard/reports/page.tsx` — Complete 13-tab dashboard with KPI cards, Recharts visualizations, date range picker with presets, table views, and CSV export.
- `src/types/reports.ts` — TypeScript interfaces matching all report schemas.
- `lib/api.ts` — API client integration for all report data and CSV downloads.

**Tests (`backend/tests/`):**
- `test_reports.py` — 28/28 passing automated tests covering all 13 reports, cross-shop isolation, date presets, custom date range validation, and voided billing exclusion.

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

### Phase 9 — Reports & Financial Analytics ✅
- 13 report endpoints: Summary, Revenue, Collection, Payment Methods, Applications, Services, Customers, Staff, Outstanding, Billing, Discounts, Financial Trend, Documents
- 13 CSV export endpoints matching each report
- Decimal/Numeric(12,2) monetary precision with string serialization in JSON
- Recharts visualizations (BarChart, LineChart, PieChart) on 13-tab frontend dashboard
- Date range picker with presets (today, yesterday, last_7_days, last_30_days, this_month, last_month, this_year, custom)
- RBAC: REPORT_VIEW (Owner, Manager, Financial Staff) and REPORT_EXPORT (Owner, Manager)
- Strict tenant isolation (shop_id) on all queries
- Cross-shop isolation verified (403 on other shop data)
- 28/28 automated tests passing
- Date preset and custom range validation tests
- Voided billing exclusion from all financial reports

---

## Next Phase (Planning)

**Phase 10 — Receipt Generation & Communication**  
Status: **PLANNED**

Phase 10 connects: **Payment → Receipt → Delivery**

Planned scope:
- Receipt model and PDF generation
- Receipt templates with branding
- Email/SMS receipt delivery
- GST/invoice compliance
- Print/preview receipt functionality

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
| Report tests | 28 | ✅ PASS |
| Phase 3.1 security tests | Multiple | ✅ PASS |
| Tenancy tests | Multiple | ✅ PASS |
| **Total** | **164** | ✅ **ALL PASS** |

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
| `/dashboard/reports` | ✅ Implemented | 13-tab Reports dashboard with charts & CSV export |
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
- `reports` — Reports & analytics (Phase 9)

---

## Last Verified State

- Phase 5.1: Customer verification completed (12/12 tests pass, frontend build passes, Docker healthy)
- Phase 6: Application management completed (23/23 tests pass, frontend build passes, Docker healthy)
- Phase 7: Document management completed (31/31 tests pass, 136 total, frontend build passes, Docker healthy)
- Phase 8: Billing & payments completed (136/136 tests pass, frontend build passes, Docker healthy, migration applied)
- Phase 9: Reports & financial analytics completed (28/28 tests pass, 164 total, frontend build passes, Docker healthy)

---

## Known Issues

None at this time — all Phase 9 deliverables complete and verified.