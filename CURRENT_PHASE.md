# Current Phase — Phase 11

## Status

**COMPLETE AND VERIFIED**

## Objective

Build a separate **Customer Portal** with its own authentication system, allowing customers to:
- Log in with email/password (shop-scoped)
- View their dashboard with applications, documents, payments summary
- Browse and track their service applications
- View and download verified documents
- View payment history
- View and edit their profile
- Change their password

## Scope

**Phase 11 includes:**

**Backend - Customer Auth Module (`backend/app/modules/customers/auth/`):**
- CustomerAuth model with Argon2id password hashing, failed login tracking, account locking
- JWT access tokens (short-lived) + HTTP-only refresh tokens (7 days, Redis-backed with revocation)
- RBAC: new permission `CUSTOMER_PORTAL_ACCESS`
- Login/refresh/logout/me endpoints (proxied through Next.js API routes)
- Change password endpoint with audit logging
- Tenant isolation via `x-shop-id` header (never trust frontend)

**Frontend - Customer Portal (`frontend/app/portal/[shopId]/`):**
- `/portal/login` — Login page with shop selection
- `/portal/[shopId]/dashboard` — Stats cards + quick actions
- `/portal/[shopId]/applications` — Paginated table with status badges + view detail
- `/portal/[shopId]/applications/[id]` — Application detail with form data
- `/portal/[shopId]/documents` — Paginated table with status, download for verified
- `/portal/[shopId]/payments` — Paginated table with method badges
- `/portal/[shopId]/profile` — View/edit profile (name, email, mobile, address)
- `/portal/[shopId]/settings` — Change password with validation
- CustomerAuthProvider context for token management (memory-only access tokens)
- API client integration (`customerPortalApi`, `customerLogin`, `customerLogout`, etc.)

**Security:**
- Separate auth system from staff/platform auth
- Argon2id password hashing (reuses existing security utilities)
- Short-lived access tokens (15 min) + HTTP-only refresh cookies
- Session revocation on logout/password change
- Failed login tracking with account lockout (5 attempts → 15 min lock)
- `x-shop-id` header for tenant isolation (shop_id from URL, validated server-side)
- Audit logging for all mutations

## Out of Scope

**The following are intentionally future modules — DO NOT IMPLEMENT:**

- Customer self-registration (admin creates accounts)
- Multi-factor authentication for customers
- Customer-facing document upload
- Customer-facing application submission
- Payment initiation from portal
- Notification preferences
- Two-factor authentication for customers

## Requirements & Implementation Status

| Requirement | Details | Status |
|-------------|---------|--------|
| CustomerAuth model | shop_id, customer_id, email, password_hash, failed_login_attempts, locked_until, last_login_at, password_changed_at | ✅ Done (`backend/app/models/customer_account.py`) |
| Login endpoint | POST `/api/customer-auth/login` with email, password, x-shop-id | ✅ Done |
| Refresh token | POST `/api/customer-auth/refresh` with x-shop-id | ✅ Done |
| Logout endpoint | POST `/api/customer-auth/logout` with token revocation | ✅ Done |
| Me endpoint | GET `/api/customer-auth/me` returns CustomerAuthUser | ✅ Done |
| Change password | POST `/api/customer-portal/{shopId}/change-password` with audit | ✅ Done |
| Profile endpoint | GET/PATCH `/api/customer-portal/{shopId}/profile` | ✅ Done |
| Applications list | GET `/api/customer-portal/{shopId}/applications` with pagination | ✅ Done |
| Application detail | GET `/api/customer-portal/{shopId}/applications/{id}` | ✅ Done |
| Documents list | GET `/api/customer-portal/{shopId}/documents` with pagination | ✅ Done |
| Payments list | GET `/api/customer-portal/{shopId}/payments` with pagination | ✅ Done |
| Login page | Form with shopId, email, password; redirects to dashboard | ✅ Done |
| Dashboard page | Stats cards, quick action links to other portal pages | ✅ Done |
| Applications page | Table with status badges, pagination, view detail link | ✅ Done |
| Application detail | Full form data display, related actions links | ✅ Done |
| Documents page | Table with status, download for verified, rejection reason | ✅ Done |
| Payments page | Table with amount, method badges, reference, recorded by | ✅ Done |
| Profile page | View/edit form with name, email, mobile, address | ✅ Done |
| Settings page | Change password form with current/new/confirm validation | ✅ Done |
| CustomerAuthProvider | React context with token management, auto-refresh | ✅ Done |
| API client | customerPortalApi, customerLogin, customerLogout, etc. | ✅ Done |
| RBAC | CUSTOMER_PORTAL_ACCESS permission enforced | ✅ Done |
| Tenant isolation | shop_id from URL validated server-side | ✅ Done |
| Audit logging | All mutations logged via existing audit system | ✅ Done |
| Frontend build | `npm run build` passes | ✅ Done |
| Backend tests | 169/169 tests pass | ✅ Done |
| Docker verification | All services healthy | ✅ Done |

## Implementation Checklist

| Task | Status | Notes |
|------|--------|-------|
| [x] CustomerAuth model | ✅ Done | `backend/app/models/customer_account.py` |
| [x] Migration for customer_accounts table | ✅ Done | `4b5174192b0d_create_customer_accounts_table_for_.py` |
| [x] Customer auth service | ✅ Done | `backend/app/modules/customers/auth/service.py` |
| [x] Customer auth router | ✅ Done | `backend/app/modules/customers/auth/router.py` |
| [x] Customer portal router | ✅ Done | `backend/app/modules/customers/portal/router.py` |
| [x] Customer portal service | ✅ Done | `backend/app/modules/customers/portal/service.py` |
| [x] RBAC permission CUSTOMER_PORTAL_ACCESS | ✅ Done | Added to `backend/app/core/roles.py` |
| [x] Audit logging integration | ✅ Done | All mutations logged |
| [x] Frontend login page | ✅ Done | `frontend/app/portal/login/page.tsx` |
| [x] Portal layout with CustomerAuthProvider | ✅ Done | `frontend/app/portal/[shopId]/layout.tsx` |
| [x] Dashboard page | ✅ Done | `frontend/app/portal/[shopId]/dashboard/page.tsx` |
| [x] Applications list page | ✅ Done | `frontend/app/portal/[shopId]/applications/page.tsx` |
| [x] Application detail page | ✅ Done | `frontend/app/portal/[shopId]/applications/[id]/page.tsx` |
| [x] Documents page | ✅ Done | `frontend/app/portal/[shopId]/documents/page.tsx` |
| [x] Payments page | ✅ Done | `frontend/app/portal/[shopId]/payments/page.tsx` |
| [x] Profile page | ✅ Done | `frontend/app/portal/[shopId]/profile/page.tsx` |
| [x] Settings page | ✅ Done | `frontend/app/portal/[shopId]/settings/page.tsx` |
| [x] CustomerAuthProvider context | ✅ Done | `frontend/lib/customer-auth-context.tsx` |
| [x] API client integration | ✅ Done | `frontend/lib/api.ts` |
| [x] Next.js 15 app router compatibility | ✅ Done | `use(params)` hook in all pages |
| [x] Backend tests pass (169/169) | ✅ Done | Verified |
| [x] Frontend build passes | ✅ Done | `npm run build` |
| [x] Docker services healthy | ✅ Done | All 5 services running |

---

## Phase 11 — Customer Portal: Technical Summary

### Backend Architecture

**Models (`backend/app/models/customer_account.py`):**
- `CustomerAuth` — Authentication table with:
  - `shop_id` (FK to shops, tenant isolation)
  - `customer_id` (FK to customers, one-to-one)
  - `email` (unique per shop)
  - `password_hash` (Argon2id)
  - `status` (active/inactive/locked)
  - `failed_login_attempts` (tracking)
  - `locked_until` (lockout timestamp)
  - `password_changed_at` (password rotation tracking)
  - `last_login_at` (activity tracking)

**Auth Module (`backend/app/modules/customers/auth/`):**
- `schemas.py` — Request/response schemas (LoginRequest, LoginResponse, ChangePasswordRequest, CustomerAuthUser)
- `service.py` — `CustomerAuthService` with:
  - `authenticate()` — Email/password verification with Argon2id, failed attempt tracking, lockout
  - `create_tokens()` — JWT access (15 min) + refresh token (7 days, stored in Redis with revocation list)
  - `refresh_tokens()` — Validate refresh token, issue new pair, rotate
  - `logout()` — Revoke refresh token, clear session
  - `get_current_customer()` — Validate access token, return CustomerAuthUser
  - `change_password()` — Verify current password, hash new, revoke all sessions, audit log
- `router.py` — Endpoints:
  - `POST /login` — Returns access_token, sets refresh_token HTTP-only cookie
  - `POST /refresh` — Reads refresh cookie, returns new access_token
  - `POST /logout` — Revokes session
  - `GET /me` — Returns customer info (requires valid access token)
- `dependencies.py` — `get_current_customer` dependency for protected routes

**Portal Module (`backend/app/modules/customers/portal/`):**
- `schemas.py` — Response schemas for applications, documents, payments, profile
- `service.py` — `CustomerPortalService` with tenant-isolated queries (all scoped by customer.shop_id and customer_id)
- `router.py` — Protected endpoints (require `get_current_customer`):
  - `GET /profile` — Customer profile
  - `PATCH /profile` — Update profile (name, email, mobile, address)
  - `POST /change-password` — Change password (delegates to auth service)
  - `GET /applications` — Paginated list
  - `GET /applications/{id}` — Detail with form_data
  - `GET /documents` — Paginated list with status
  - `GET /payments` — Paginated list

### Frontend Architecture

**Auth Context (`frontend/lib/customer-auth-context.tsx`):**
- `CustomerAuthProvider` — Manages customer auth state:
  - In-memory access token (never localStorage)
  - Auto-refresh before expiry
  - `login()`, `logout()`, `refresh()` methods
  - `customer` state (CustomerAuthUser) and `ready` flag
- `useCustomerAuth()` hook for consuming auth state

**API Client (`frontend/lib/api.ts`):**
- Separate token management for customer portal (`customerAccessToken`, `customerAccessTokenExpiry`)
- `customerLogin(email, password, shopId)` — Calls `/api/customer-auth/login`
- `customerRefreshToken(shopId)` — Calls `/api/customer-auth/refresh`
- `customerLogout()` — Calls `/api/customer-auth/logout`
- `fetchCurrentCustomer(shopId)` — Calls `/api/customer-auth/me`
- `customerPortalApi` — Object with methods for all portal endpoints (listApplications, getApplication, listDocuments, listPayments, getProfile, updateProfile, changePassword)

**Portal Pages (`frontend/app/portal/[shopId]/`):**
All pages updated for Next.js 15 App Router (`params` is `Promise<{ shopId: string }>`):
- Use `use(params)` hook to resolve params
- Use `customer!.shop_id` (number from auth context) for API calls (tenant isolation enforced server-side)
- Proper loading/error/empty states
- Responsive UI with Tailwind CSS + shadcn/ui components

### Security Features

1. **Separate Auth System** — Completely independent from staff/platform authentication
2. **Argon2id** — Industry-standard password hashing (reuses `backend/app/core/security.py`)
3. **Short-lived Access Tokens** — 15 minutes, stored only in memory
4. **HTTP-only Refresh Cookies** — 7 days, secure, same-site, not accessible to JS
5. **Session Revocation** — On logout and password change (Redis-backed revocation list)
6. **Account Lockout** — 5 failed attempts → 15 minute lock
7. **Tenant Isolation** — `shop_id` from URL validated against authenticated customer's shop_id
8. **Audit Logging** — All mutations (login, logout, password change, profile update) logged via existing audit system
9. **Password Policy** — Minimum 8 chars, uppercase, lowercase, digit, special char enforced on change

### Test Verification

- **Backend**: 169/169 tests pass (no regressions from existing phases)
- **Frontend**: `npm run build` passes with no TypeScript errors
- **Docker**: All 5 services healthy (frontend, backend, postgres, redis, minio)
- **Manual QA**: Login → dashboard → applications → documents → payments → profile → settings → password change flow verified

---

## Next Phase (Planning)

**Phase 12 — Final Polish & Release Preparation**  
Status: **PLANNED**

Phase 12 focuses on production readiness:

Planned scope:
- End-to-end integration testing
- Performance optimization
- Security audit
- Documentation completion
- Deployment guides
- Release notes