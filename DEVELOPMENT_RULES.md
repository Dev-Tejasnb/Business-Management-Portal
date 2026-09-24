# Development Rules

Permanent instructions for every AI/coding session. Read this file before starting work.

## Rule 1 — Inspect Before Editing

Always inspect the repository before making changes.

## Rule 2 — Read Continuity Files

Before starting work, read:
- PROJECT_STATUS.md
- DEVELOPMENT_RULES.md
- PHASE_HISTORY.md
- CURRENT_PHASE.md

## Rule 3 — Never Reimplement Completed Phases

Completed phases are stable. Do not rewrite them unnecessarily.

## Rule 4 — Search Before Creating

Before creating:
- model
- service
- router
- permission
- utility
- component

Search the repository first. Reuse existing functionality.

## Rule 5 — Never Modify Old Migrations Unnecessarily

Never modify historical migrations. Create a new migration for new schema changes.

## Rule 6 — Never Trust Frontend Security

Backend must validate:
- shop_id
- user
- role
- permissions
- customer_id
- service_id
- staff_id

## Rule 7 — Tenant Isolation

Every tenant-owned record must be scoped by shop_id. Never allow cross-shop access.

## Rule 8 — RBAC

Use dedicated permissions. Do not reuse unrelated permissions.

## Rule 9 — Audit

Mutations must use the existing AuditService. Old/new values must be accurate. Actor identity must be server-derived.

## Rule 10 — No Hard Delete Where History Matters

Prefer archive/status lifecycle for business records.

## Rule 11 — Test Before Declaring Complete

Run:
- backend tests
- frontend build
- relevant integration tests
- Docker verification

## Rule 12 — Never Delete Tests

Never weaken or delete tests merely to make a build pass.

## Rule 13 — Fix Only Relevant Issues

Do not expand scope unnecessarily.

## Rule 14 — No Premature Future Modules

Do not implement future phases early.

## Rule 15 — Protect Existing Features

After changes, verify previous modules still pass.

## Rule 16 — Git Safety

Check:
- git status
- git diff --stat
- git diff

before completing work.

## Rule 17 — Secrets

Never commit:
- .env
- passwords
- API keys
- JWT secrets
- database credentials

## Rule 18 — Interrupted Sessions

If a previous AI session was interrupted:
**DO NOT START AGAIN FROM ZERO.**
Inspect existing code and continue from the actual state.

## Rule 19 — Checkpoint Progress

After every major implementation step:
- test
- record result
- continue

## Rule 20 — Stop At Scope Boundary

When the requested phase is complete:
**STOP.**
Do not automatically start the next phase.