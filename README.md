# Business Management Portal

An all-in-one web application (SaaS) for service-based businesses: CSC / Common
Service Centers, GramaOne / Government Service Centers, online service centers,
Xerox & printing shops, cyber cafes, and digital service businesses.

> **Status: Phase 2 — Authentication, Users, Shops, RBAC, Tenancy & Audit Logging complete.**
> Business modules (customers, applications, services, billing, staff, documents, analytics, etc.)
> will be implemented in subsequent phases.

---

## 1. Purpose & Architecture

A multi-tenant platform where each shop/business is a **tenant**, with the core
business flow:

```
Customer → Service → Application → Documents → Payment → Status → Completion
```

- **Tenancy**: Multi-tenant via `shop_id` isolation. Tenant identity is resolved **strictly server-side** from authenticated memberships — never trusted from request bodies or client headers.
- **Identity & Membership**: Users have a platform-level identity. Affiliation with shops is modeled via `ShopMembership` records, enabling multi-shop membership.
- **RBAC**: Centralized role-based access control with discrete permission constants for both platform-level and shop-level scopes.
- **Audit Logging**: Centralized, append-only audit trail for all security events and critical entity mutations.
- **Passwords**: Hashed with Argon2id (salt + memory-hard hashing).
- **Sessions / Tokens**: Short-lived JWT access tokens held only in-memory; opaque refresh tokens stored in Redis with server-side revocation and delivered via HTTP-only cookies.

---

## 2. Technology Stack

| Layer     | Technology                                        |
|-----------|---------------------------------------------------|
| Frontend  | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Backend   | Python 3.13, FastAPI, Pydantic 2.x                |
| ORM       | SQLAlchemy 2.x (async with asyncpg)               |
| Migrations| Alembic                                          |
| Database  | PostgreSQL 16                                     |
| Cache/Auth| Redis 7                                           |
| Storage   | MinIO (S3-compatible object storage)             |
| Infra     | Docker, Docker Compose v2                         |
| Testing   | Pytest, pytest-asyncio, HTTPX                     |
| Security  | Argon2id (argon2-cffi), PyJWT                     |

---

## 3. Roles & Permissions

### Platform Roles (Platform Scope)
- **Platform Owner** (`platform_owner`): Full platform administration, shop creation, user management, audit review.
- **Platform Admin** (`platform_admin`): Platform administration, shop lifecycle, user management.
- **Platform Manager** (`platform_manager`): Shop management, user viewing, audit review.
- **Platform Financial Manager** (`platform_financial_manager`): Financial reporting and billing overview.
- **Platform Support** (`platform_support`): Read-only viewing of shops and users for support.

### Shop Roles (Shop/Tenant Scope)
- **Shop Owner** (`shop_owner`): Full control within their tenant (settings, staff, billing, operations).
- **Shop Manager** (`shop_manager`): Daily operations management, staff viewing, service operations.
- **Staff / Service Staff** (`staff`): Processing customer applications and document handling.
- **Financial Staff** (`financial_staff`): Payments, invoicing, and billing records within the shop.

---

## 4. API Endpoints (v1)

### Health
- `GET /health` — Liveness probe (no dependencies).
- `GET /api/v1/health` — Readiness probe (PostgreSQL, Redis, MinIO).

### Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/login` — Authenticate with email/password; returns access token and sets HTTP-only refresh cookie.
- `POST /api/v1/auth/refresh` — Rotate refresh session via cookie and return a new access token.
- `POST /api/v1/auth/logout` — Revoke session in Redis and clear the refresh cookie.
- `GET /api/v1/auth/me` — Return current authenticated user profile.

### Shops & Tenancy (`/api/v1/shops`)
- `POST /api/v1/shops` — Create a new shop (Platform Owner/Admin only).
- `GET /api/v1/shops` — List all shops (Platform permissions).
- `GET /api/v1/shops/{shop_id}` — Get shop details (Platform user or active shop member).
- `GET /api/v1/shops/{shop_id}/memberships/me` — Get current user's membership in a shop (verifies tenant isolation).
- `POST /api/v1/shops/{shop_id}/memberships` — Add a user to a shop (Shop Owner / Platform Admin).
- `GET /api/v1/shops/{shop_id}/memberships` — List memberships for a shop (Shop Manager/Owner).

---

## 5. Development Setup & Commands

### 1. Configure Environment
```bash
cp .env.example .env
```

### 2. Start Services with Docker Compose
```bash
docker compose up --build
```

### 3. Run Database Migrations
```bash
docker compose exec backend alembic upgrade head
```

### 4. Bootstrap Initial Platform Owner (Development)
```bash
docker compose exec backend python -m app.scripts.bootstrap_platform_owner
```

### 5. Run Backend Tests
```bash
docker compose exec backend pytest -v
```

---

## 6. Accessing the Application

- **Frontend**: `http://localhost:3000`
- **Login Page**: `http://localhost:3000/login`
- **Dashboard (Protected)**: `http://localhost:3000/dashboard`
- **API Docs (Swagger)**: `http://localhost:8000/docs`
- **Liveness Probe**: `http://localhost:8000/health`
- **Readiness Probe**: `http://localhost:8000/api/v1/health`
- **MinIO Console**: `http://localhost:9001`
