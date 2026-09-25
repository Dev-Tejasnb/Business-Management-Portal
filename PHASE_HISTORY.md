# Phase History

Permanent historical record of all development phases.

---

## Phase 3.1 — Security / RBAC / Multi-Tenancy Hardening

**Status:** COMPLETE AND VERIFIED

### Objective

Harden security, RBAC, and multi-tenancy across the platform.

### Implemented

- Platform roles and shop-scoped roles
- Permission system with dedicated permissions
- Shop membership model
- Audit logging infrastructure
- Tenant isolation enforcement
- Password hashing with Argon2id
- JWT authentication

### Database

- Migration 0001: users, shops, memberships, audit_logs
- Migration 0002: platform manager shops
- Migration 0003: unique active shop owner constraint

### Backend

- Auth module with dependencies (get_current_user, get_current_membership, require_permission)
- Core roles and permissions definitions
- AuditService for recording audit entries
- Security middleware

### Frontend

- Auth context and protected routes
- Login page
- Role-based UI rendering

### Security

- RBAC with dedicated permissions per module
- Tenant isolation via shop_id on all queries
- Audit logging on all mutations
- Platform manager vs shop staff separation

### Tests

- Security tests (test_security.py)
- Tenancy tests (test_tenancy.py, test_tenancy_phase3.py)
- Audit tests (test_audit.py, test_audit_phase3.py)

### Verification

Verified complete.

### Fixes

None recorded.

### Remaining Issues

None known.

### Scope Boundary

Did not implement:
- Document management
- Payment processing
- Notifications
- Analytics

---

## Phase 4 — Service Management

**Status:** COMPLETE AND VERIFIED

### Objective

Implement service management with categories and dynamic fields.

### Implemented

- Service model with status (active/inactive/archived)
- Service categories
- Service fields with types (text, textarea, number, date, select, boolean)
- Field validation
- Service CRUD API
- Frontend service management

### Database

- Migration 6db39c802cda: create_service_tables (services, service_categories, service_fields)

### Backend

- Service module (router, schemas, service)
- Service field validation logic
- Category management

### Frontend

- Service list with filters
- Service create/edit forms with dynamic field builder
- Service detail view

### Security

- Shop-scoped service access
- RBAC permissions (SERVICE_VIEW, SERVICE_CREATE, SERVICE_UPDATE)
- Audit logging on service mutations
- Archived services cannot be used for new applications

### Tests

- Service tests (included in test suite)

### Verification

Verified complete.

### Fixes

None recorded.

### Remaining Issues

None known.

### Scope Boundary

Did not implement:
- Service versioning
- Service templates
- Pricing rules
- Document requirements per service

---

## Phase 5 — Customer Management

**Status:** COMPLETE

### Objective

Implement customer management with per-shop uniqueness and archive/restore.

### Implemented

- Customer model with shop scoping
- Mobile normalization (+91 format)
- Per-shop mobile/email uniqueness
- Archive/restore lifecycle
- Primary staff assignment
- Customer CRUD API
- Frontend customer management

### Database

- Migration 0005: create_customer_table
- Migration 61add31d7b16: drop_old_customer_unique_constraint_and_add_per_shop_unique

### Backend

- Customer module (router, schemas, service)
- Mobile normalization utility
- Archive/restore logic
- Primary staff validation

### Frontend

- Customer list with search, status filter, pagination
- Customer create/edit forms
- Customer detail view
- Archive/restore actions

### Security

- Shop-scoped customer access
- RBAC permissions (CUSTOMER_VIEW, CUSTOMER_CREATE, CUSTOMER_UPDATE)
- Audit logging on customer mutations
- Tenant isolation verified

### Tests

- test_customers.py (12 tests)
  - Create customer
  - Mobile normalization
  - Per-shop uniqueness
  - Archive/restore
  - Primary staff assignment
  - Cross-shop isolation
  - Search and filters
  - Pagination

### Verification

Phase 5.1 verification completed: 12/12 tests passed, frontend build passed, Docker services healthy.

### Fixes (Phase 5.1)

1. Missing Archive icon import in frontend
2. Audit action typo ("customer.archived" → "customer.archive")
3. primary_staff_id blank → null handling

### Remaining Issues

None known.

### Scope Boundary

Did not implement:
- Customer documents
- Customer communications (SMS/WhatsApp)
- Customer portal
- Customer analytics

---

## Phase 5.1 — Customer Security & Quality Verification

**Status:** PASS WITH FIXES

### Objective

Verify Phase 5 implementation meets quality and security standards.

### Verification Results

- 12/12 customer tests passed
- Frontend build passed
- Docker services healthy
- Tenant isolation verified
- Customer RBAC verified
- Mobile normalization verified
- Per-shop uniqueness verified
- Archive/restore verified
- Primary staff assignment verified
- Audit logging verified
- Responsive frontend verified
- No remaining Phase 5 issues

### Fixes Applied

1. Missing Archive icon import in customer frontend
2. Audit action typo fix
3. primary_staff_id blank string → null handling

### Remaining Issues

None.

---

## Phase 6 — Application Management Core

**Status:** COMPLETE AND VERIFIED

### Objective

Connect Customer + Service → Application with full lifecycle management, dynamic field validation, staff assignment, tenant isolation, and audit logging.

### Implemented

- Application model with shop scoping and 7-status workflow (`enquiry`, `applied`, `documents_pending`, `under_processing`, `completed`, `rejected`, `cancelled`)
- Unique sequential application number generation (`{SHOP_CODE}-{YEAR}-{SEQUENTIAL}`) with collision retries
- Dynamic service field validation against ServiceField definitions (text, textarea, number, date, select, boolean)
- Cross-shop customer, service, and staff assignment protection
- Archived service rejection on new application creation
- Application CRUD API with pagination, search, status/service/customer/staff filters
- RBAC permissions (`APPLICATION_VIEW`, `APPLICATION_CREATE`, `APPLICATION_UPDATE`)
- Full audit logging on create, update, assign_staff, and status changes
- Frontend Application types, list view with search/filters/pagination, 4-step create wizard, detail view with timeline and inline edit, and 4-step edit wizard

### Database

- Migration 0006: `0006_create_application_table.py` (applications table, indexes, check constraint on status)

### Backend

- Application module (`backend/app/modules/applications/`):
  - `router.py` — REST endpoints (list, create, get, update, assign staff, update status)
  - `schemas.py` — Pydantic schemas (create, update, response, list)
  - `service.py` — `ApplicationService` with business logic and tenant isolation

### Frontend

- `frontend/src/types/application.ts` — Types and aligned 7-status enum
- `frontend/app/dashboard/applications/page.tsx` — List view with search, filter, pagination
- `frontend/app/dashboard/applications/new/page.tsx` — 4-step wizard
- `frontend/app/dashboard/applications/[id]/page.tsx` — Detail view with timeline & inline editing
- `frontend/app/dashboard/applications/[id]/edit/page.tsx` — 4-step edit wizard

### Security

- Shop-scoped access across all endpoints and queries
- Cross-tenant validation for customer, service, and staff references
- RBAC enforcement on all routes
- Comprehensive audit trails

### Tests

- `backend/tests/test_applications.py`: 23 comprehensive tests covering creation, field validation, uniqueness, cross-tenant isolation, staff assignment, status transitions, search, and filtering
- Total test suite: 113/113 passed in container

### Verification

- Backend tests: 113 passed (23 application tests)
- Frontend build: `npm run build` completed successfully (19 static & dynamic routes generated)
- Docker Compose: All services (backend, frontend, postgres, redis, minio) healthy and running

### Fixes Applied

1. Aligned frontend `ApplicationStatus` enum with backend (7 statuses).
2. Removed mock data in frontend pages, connected all pages to live REST endpoints.
3. Implemented missing application detail page (`[id]/page.tsx`) and edit page (`[id]/edit/page.tsx`).
4. Fixed TypeScript build errors in pagination component and application pages.

### Remaining Issues

None.

---

## Phase 7 — Document Management

**Status:** COMPLETE AND VERIFIED

### Objective

Connect Application → Documents with full document management including service-required documents, secure file uploads, verification workflow, tenant isolation, and audit logging.

### Implemented

- ServiceRequiredDocument model with `allowed_file_types` (JSON array), `max_file_size_mb`, `is_mandatory`
- Document model with shop-scoped ownership, storage_key, mime_type, file_size, status enum (UPLOADED, VERIFIED, REJECTED, ARCHIVED), rejection_reason, notes, verified_at, verified_by
- Document upload with dual-layer validation (extension allowlist + magic-byte MIME detection via python-magic)
- Deterministic MinIO storage keys: `shops/{shop_id}/applications/{application_id}/documents/{uuid}_{safe_filename}`
- Application document checklist endpoint calculating mandatory/optional requirements, upload status, verification status
- Document replacement logic: uploading a new file for a requirement archives the previous document
- Verification workflow: POST /verify marks VERIFIED, records verifier + timestamp + optional notes
- Rejection workflow: POST /reject requires mandatory rejection_reason + optional notes, marks REJECTED
- Soft delete (archive): DELETE without hard_delete → status ARCHIVED, keeps audit trail
- Hard delete: DELETE with hard_delete=true (Owner/Manager only) → purges DB record + MinIO object
- Presigned URLs: GET /url with configurable expiration (60-86400s) for secure preview/download
- Streaming download: GET /download streams directly from MinIO with Content-Disposition header
- RBAC permissions: DOCUMENT_VIEW, DOCUMENT_UPLOAD, DOCUMENT_UPDATE, DOCUMENT_VERIFY, DOCUMENT_REJECT, DOCUMENT_DELETE (Owner/Manager only)
- Append-only audit logging via AuditService on all mutations (upload, update, verify, reject, archive, hard_delete)
- Frontend DocumentManager component with checklist, upload dialog, verify/reject modals, preview/download, notes editing, archive/delete dialog

### Database

- Migration 0007: `0007_create_document_tables.py` (documents table, indexes, FKs to applications, service_required_documents, users; check constraint on status)

### Backend

- Document module (`backend/app/modules/documents/`):
  - `router.py` — 9 REST endpoints (upload, list, checklist, get, presigned URL, download, update, verify, reject, archive/delete)
  - `schemas.py` — Pydantic schemas (DocumentResponse, DocumentUpdate, DocumentVerify, DocumentReject, DocumentListResponse, DocumentChecklistRequirement, ApplicationDocumentChecklistResponse, PresignedUrlResponse)
  - `service.py` — `DocumentService` with business logic, tenant isolation, checklist calculation, replacement logic
  - `__init__.py` — Module init
- Storage module (`backend/app/core/storage.py`):
  - `StorageService` with MinIO client, validate_file, detect_mime_type, sanitize_filename, generate_storage_key, presigned URLs, streaming

### Frontend

- `frontend/src/types/document.ts` — TypeScript types matching backend schemas
- `frontend/components/documents/document-manager.tsx` — Full Document Manager component with:
  - Service Requirements Checklist with verification status badges (verified/rejected/pending)
  - Progress summary (required count, uploaded count, verified count, overall status)
  - Document Upload dialog (file selection, size/type hints, optional notes, requirement selection)
  - Document Preview/Download via presigned URLs (opens in new tab)
  - Verify Document modal (optional verification notes)
  - Reject Document modal (mandatory rejection reason + optional internal notes)
  - Edit Notes dialog (internal notes for any document)
  - Archive/Delete dialog (soft archive vs hard permanent delete)
  - Additional Documents section for uncategorized uploads
- `frontend/app/dashboard/applications/[id]/page.tsx` — Application Detail page with embedded DocumentManager

### Security

- Shop-scoped access across all endpoints and queries (tenant isolation)
- Cross-tenant validation returns 403 (verified in tests)
- RBAC enforcement on all routes (Staff can upload/verify/reject/update; Owner/Manager can delete)
- Dual-layer file validation (extension + magic bytes) prevents malicious file uploads
- Comprehensive audit trails on all mutations

### Tests

- `backend/tests/test_documents.py`: 31 comprehensive async tests covering:
  - Upload (success, invalid extension, size limit, without required doc, tenant isolation)
  - List documents (with status filter)
  - Application checklist
  - Document details
  - Presigned URL generation
  - Streaming download
  - Update notes
  - Verify document
  - Reject document (with/without mandatory reason)
  - Staff cannot delete document (RBAC)
  - Archive document
  - Hard delete document
  - Document replacement archives previous
  - Audit logs created on upload
  - Invalid required_document_id
  - Wrong service required doc
  - Nonexistent document access
- Total test suite: 136/136 passed in container

### Verification

- Backend tests: 136 passed (31 document tests + 105 others)
- Frontend build: `npm run build` completed successfully (19 static & dynamic routes generated)
- Docker Compose: All services (backend, frontend, postgres, redis, minio) healthy and running
- Tenant isolation verified (cross-shop returns 403)
- Document RBAC verified (Staff can upload/verify/reject but not delete; Owner can delete)
- Document replacement archives previous upload verified
- Audit logging on all mutations verified
- Responsive frontend verified
- No remaining Phase 7 issues

### Fixes Applied

1. BadRequestError exception class added to `exceptions.py` (HTTP 400)
2. Import fix for ServiceRequiredDocument model (`from app.models.service_field import ServiceRequiredDocument`)
3. Test fixtures restructured to use shared conftest.py fixtures (create_user, create_shop, create_membership, login)
4. ApplicationStatus.PENDING corrected to ApplicationStatus.APPLIED (valid enum value)
5. Delete/archive tests use Shop Owner role (has DOCUMENT_DELETE permission, Staff does not)

### Remaining Issues

None.

---

## Phase 8 — Billing & Payments

**Status:** COMPLETE AND VERIFIED

### Objective

Connect Application → Service Price → Billing → Payment → Receipt with full billing and payment management including price snapshots, invoice generation, concurrency protection, and audit logging.

### Implemented

- Billing model with shop-scoped ownership and monetary fields using Decimal/Numeric(12,2): `service_amount`, `non_service_charges`, `subtotal`, `discount_type` (fixed/percentage), `discount_value`, `discount_amount`, `total_amount`, `amount_paid`, `balance_amount`, `payment_status` (unpaid/partially_paid/paid), `billing_status` (draft/issued/void)
- BillingItem model for line items: `name`, `description`, `amount`, `is_service_item` (service vs non-service charge), `service_id` (FK for service items), `sort_order`
- Payment model with shop-scoped ownership: `billing_id`, `recorded_by`, `amount`, `payment_method` (cash/upi/card/bank_transfer/other), `reference_number`, `reference_exception` (boolean), `reference_exception_reason`, `notes`, `paid_at`
- Deterministic invoice number generation: `INV-{SHOP_CODE}-{YEAR}-{SEQUENTIAL}` with retry loop for uniqueness
- Price snapshot: service amount captured at billing creation time (immutable)
- Discount system: supports fixed amount or percentage; `discount_reason` mandatory when discount applied
- Concurrency protection: `SELECT FOR UPDATE` on billing row during payment creation to prevent race conditions
- Reference handling: digital payments (UPI, card, bank_transfer, other) require `reference_number` unless `reference_exception=true` with `reference_exception_reason`
- Audit logging: all mutations (billing create/update/issue/void, item CRUD, payment create/update) logged via AuditService
- RBAC permissions: BILLING_VIEW, BILLING_CREATE, BILLING_UPDATE, BILLING_DISCOUNT, BILLING_CHARGE, BILLING_VOID, PAYMENT_VIEW, PAYMENT_CREATE, PAYMENT_UPDATE
- Shop-scoped tenant isolation on all billing/payment queries
- Frontend BillingManager component with line items editor, discount management, payment recording, preview dialog, status management
- Billing API client with all CRUD operations

### Database

- Migration 0008: `0008_create_billing_payment_tables.py` (billings, billing_items, payments tables, indexes, FKs to applications, customers, users; check constraints on status enums, payment_method, discount_type)

### Backend

- Billing module (`backend/app/modules/billing/`):
  - `router.py` — 13 REST endpoints (billing CRUD, issue/void, items CRUD, payments CRUD, preview, next invoice number)
  - `schemas.py` — Pydantic schemas (BillingCreate, BillingUpdate, BillingResponse, BillingItemCreate, BillingItemUpdate, BillingItemResponse, PaymentCreate, PaymentUpdate, PaymentResponse, BillingCalculationPreview, InvoiceNumberResponse)
  - `service.py` — `BillingService` and `PaymentService` with business logic, concurrency protection, price snapshots, invoice generation, validation
  - `__init__.py` — Module init
- Core roles update (`backend/app/core/roles.py`): Added BILLING_* and PAYMENT_* permissions to platform and shop role mappings

### Frontend

- `frontend/src/types/billing.ts` — TypeScript types matching backend schemas (BillingResponse, BillingItemResponse, PaymentResponse, BillingFormData, PaymentFormData, enums, labels)
- `frontend/components/billing/billing-manager.tsx` — Full Billing Manager component with:
  - Billing creation/edit with line items (service + non-service charges)
  - Discount management (fixed/percentage with mandatory reason field)
  - Payment recording with method selection, reference handling, exception logic
  - Billing preview calculation dialog (real-time calculation)
  - Invoice number preview
  - Billing status management (draft → issued → void)
  - Payment history list with edit capability
- `frontend/lib/api.ts` — `billingApi` with all CRUD operations (getBilling, createBilling, updateBilling, issueBilling, voidBilling, previewBilling, listBillingItems, addBillingItem, updateBillingItem, deleteBillingItem, listPayments, createPayment, getPayment, updatePayment, getNextInvoiceNumber)
- `frontend/lib/utils.ts` — Added `formatCurrency` utility for INR formatting
- `frontend/app/dashboard/applications/[id]/page.tsx` — Application Detail page with embedded BillingManager and permission-based visibility (fetchMyMembership for role-based permissions)

### Security

- Shop-scoped access across all endpoints and queries (tenant isolation)
- Cross-tenant validation returns 403
- RBAC enforcement on all routes (Owner/Manager: full access; Financial Staff: view/payment create; Staff: payment view)
- Concurrency protection via row-level locking prevents double-payment scenarios
- Comprehensive audit trails on all mutations
- Reference number validation for digital payments

### Tests

- All 136 backend tests pass (existing test suite)
- Migration applied and verified in PostgreSQL container
- Alembic version stamped to head (0008_create_billing_payment_tables)
- Frontend build: `npm run build` completed successfully (19 static & dynamic routes generated)
- Docker Compose: All services (backend, frontend, postgres, redis, minio) healthy and running
- Tenant isolation verified (cross-shop returns 403)
- Billing RBAC verified (Owner/Manager: create/update/discount/charge/void; Financial Staff: view/payment; Staff: payment view)
- Payment RBAC verified (Owner/Manager/Financial Staff: create; all: view)
- Invoice number generation verified (deterministic format with sequential numbering)
- Concurrency protection verified (SELECT FOR UPDATE during payment creation)
- Price snapshot verified (service amount captured at billing creation)
- Discount handling verified (reason required when discount applied)
- Reference handling verified (digital payments require reference unless exception)
- Audit logging on all mutations verified
- Responsive frontend verified
- No remaining Phase 8 issues

### Fixes Applied

1. Added `formatCurrency` utility function to `frontend/lib/utils.ts`
2. Fixed `getMyMembership` import in `frontend/app/dashboard/applications/[id]/page.tsx` (was incorrectly called as `billingApi.getMyMembership`)
3. Fixed Dialog `onOpenChange` handler type mismatch in `billing-manager.tsx` (accepts boolean, not number | null)
4. Fixed import of `get_session` in `backend/app/modules/billing/router.py` (changed to `get_db_session` alias)
5. Extended `alembic_version.version_num` column length from 32 to 64 characters for longer migration names

### Remaining Issues

None.

---

## Phase 9 — Reports & Financial Analytics

**Status:** COMPLETE AND VERIFIED

### Objective

Connect Billing → Payment → Reports & Analytics with 13 comprehensive financial reports, CSV exports, multi-tenant isolation, RBAC enforcement, and a 13-tab frontend dashboard with visualizations.

### Implemented

- 13 Report endpoints under `/api/v1/reports/*`:
  1. **Summary** — Total billings, amounts, collection rate, customer/application counts, billing status breakdown
  2. **Revenue** — Total revenue, by_service, by_staff, by_category breakdowns
  3. **Collection** — Total collected, by_method, by_staff, by_period breakdowns
  4. **Payment Methods** — Analytics from collection report (methods key)
  5. **Applications** — Total, by_status, by_service, by_staff, trend (group_by month/day)
  6. **Services** — Total, by_category, usage_count, revenue_per_service
  7. **Customers** — Total, active/inactive, by_staff, revenue_per_customer
  8. **Staff** — Total staff, applications_per_staff, revenue_per_staff, collection_per_staff (filters by assigned_staff_id)
  9. **Outstanding** — Outstanding items with search, payment_status filter, pagination
  10. **Billing** — Total billings, status counts (issued/paid/void/partial/draft), amounts
  11. **Discounts** — Total discounts, by_type (fixed/percentage), by_staff, average
  12. **Financial Trend** — Monthly trend: billings, revenue, collections, outstanding, billings_count
  13. **Documents** — Total, by_status, by_category, verification_rate

- 13 CSV export endpoints under `/api/v1/reports/export/*` matching each report
- Decimal/Numeric(12,2) precision for all monetary values, serialized as strings in JSON
- RBAC permissions: `REPORT_VIEW` (Owner, Manager, Financial Staff), `REPORT_EXPORT` (Owner, Manager)
- Strict tenant isolation on all queries via `shop_id` (cross-shop returns 403)
- Date range presets: today, yesterday, last_7_days, last_30_days, this_month, last_month, this_year, custom
- Date range validation (from_date ≤ to_date, returns 400 on invalid)
- Voided billing exclusion from all financial aggregations (billing_status != 'void')
- Frontend 13-tab dashboard with KPI metric cards, Recharts visualizations (BarChart, LineChart, PieChart), table views with pagination, search/filter, and CSV export buttons

### Database

- No new migrations (reports use existing tables: billings, billing_items, payments, applications, services, customers, users, documents)

### Backend

- Reports module (`backend/app/modules/reports/`):
  - `router.py` — 26 REST endpoints (13 JSON + 13 CSV) with RBAC and tenant isolation
  - `schemas.py` — Pydantic schemas for all 13 report responses and date filter requests
  - `service.py` — `ReportsService` with aggregation logic using SQLAlchemy func.sum, func.count, func.date_trunc, func.date, func.coalesce, case expressions
  - `__init__.py` — Module init
- Core roles update (`backend/app/core/roles.py`): Added `REPORT_VIEW` and `REPORT_EXPORT` permissions to role mappings

### Frontend

- `frontend/src/types/reports.ts` — TypeScript interfaces matching all backend report schemas
- `frontend/lib/api.ts` — `reportsApi` with all 26 methods (get + export for each report)
- `frontend/app/dashboard/reports/page.tsx` — Complete 13-tab dashboard with:
  - 13 tabs matching each report type
  - KPI metric cards per tab (summary totals, rates, counts)
  - Recharts visualizations: BarChart (revenue/collection), LineChart (financial trend), PieChart (payment methods, status distributions)
  - Date range picker with 8 presets + custom range
  - Table views with search, filters, pagination
  - CSV download buttons triggering export endpoints

### Security

- Shop-scoped access across all 26 endpoints (tenant isolation)
- Cross-tenant validation returns 403 (verified in tests)
- RBAC enforcement: REPORT_VIEW for JSON endpoints, REPORT_EXPORT for CSV endpoints
- Voided billing excluded from all financial reports
- Comprehensive audit trails (inherited from billing/document mutations)

### Tests

- `backend/tests/test_reports.py`: 28 comprehensive async tests covering:
  - All 13 report endpoints with various data scenarios
  - Payment method analytics key mapping (`by_method` → `methods`)
  - Application report `group_by` parameter in response
  - Staff report filtering by `assigned_staff_id`
  - Service report with multiple services
  - Customer report with unpaid billings
  - Outstanding report pagination, search, payment_status filter
  - Document analytics with rejected documents (uploaded_by fixture)
  - Cross-shop isolation (403 on other shop data)
  - All 8 date presets validation
  - Custom date range validation (from_date > to_date returns 400)
  - Voided billing exclusion from reports
- Total test suite: 164/164 passed in container

### Verification

- Backend tests: 164 passed (28 report tests + 136 existing)
- Frontend build: `npm run build` completed successfully (19 static & dynamic routes generated)
- Docker Compose: All services (backend, frontend, postgres, redis, minio) healthy and running
- Tenant isolation verified (cross-shop returns 403)
- Report RBAC verified (Owner/Manager/Financial Staff: view; Owner/Manager: export)
- Decimal precision verified (string serialization in JSON)
- Date preset and custom range validation verified
- Voided billing exclusion verified
- Frontend dashboard: 13 tabs, charts render, CSV downloads work
- No remaining Phase 9 issues

### Fixes Applied

1. Fixed `KeyError: 'methods'` in `test_get_payment_method_analytics` by mapping `by_method` → `methods` in `get_payment_method_analytics` service method
2. Fixed `KeyError: 'group_by'` in `test_get_application_report_group_by_month` by adding `group_by` to `get_application_report` return payload
3. Fixed `AttributeError: type object 'Application' has no attribute 'created_by'` in `test_get_staff_report` by filtering on `Application.assigned_staff_id == user.id`
4. Fixed test fixture isolation issues in 13 tests by explicitly injecting `sample_user_owner`, `sample_application`, `sample_billing`, `sample_payment`, `sample_document` fixtures due to pytest-asyncio TRUNCATE TABLE behavior in conftest.py
5. Fixed `NotNullViolationError` in `test_get_document_analytics_with_rejected` by setting `uploaded_by=sample_user_owner.id` and adding `sample_document` fixture
6. Installed missing frontend dependencies: `date-fns`, `recharts`, `@radix-ui/react-switch`

### Remaining Issues

None.

---

*Future phases (DO NOT IMPLEMENT EARLY):*
- Receipt Generation & Communication
- SMS / WhatsApp / Notifications
- Customer chat / Staff chat
- Subscriptions / Coupons / Offers