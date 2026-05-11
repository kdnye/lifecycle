# FSI Lifecycle — Architecture

## System Overview

```
[Browser / Mobile]
        |
        | HTTPS
        v
[Cloud Run: lifecycle (this app)]
        |
        |-- Flask Blueprints (auth, account, dashboard, intake,
        |                     internal, webhooks, inventory)
        |
        |-- app/services/          # Business logic layer
        |     ├── workflow.py       # Lifecycle event orchestration
        |     ├── email.py          # Postmark dispatch
        |     ├── inventory_service # Inventory CRUD
        |     └── asset_storage.py  # GCS photo upload
        |
        |-- Cloud SQL (PostgreSQL) ---- [kdnye/expenses owns `users`]
        |     ├── users             (read-only from lifecycle)
        |     ├── intake_request
        |     ├── inventory
        |     ├── asset_categories
        |     ├── role_matrix
        |     ├── question_matrix
        |     ├── action_matrix
        |     └── communication_options
        |
        |-- Google Cloud Storage
        |     └── {ASSET_PHOTOS_BUCKET}/assets/{id}/*.jpg
        |
        └── Postmark API
              ├── Transactional email (onboarding/offboarding dispatches)
              └── Inbound webhook (inventory intake from email)
```

---

## Request Lifecycle

1. Request arrives at Cloud Run.
2. `attach_current_user` (`before_request`) loads `g.current_user` from `session["fsi_user_id"]`.
3. Flask routes to the matching Blueprint view.
4. View calls service layer functions.
5. Service layer interacts with SQLAlchemy models / GCS / Postmark.
6. View renders Jinja2 template extending `base.html` (Bootstrap 5.3.3, FSI tokens).

---

## Blueprint Breakdown

| Blueprint | Prefix | Purpose |
|---|---|---|
| `auth_bp` | `/auth` | Login, OAuth callback, logout |
| `account_bp` | `` | Profile, communication options, theme toggle |
| `dashboard_bp` | `` | Homepage / intake activity metrics |
| `intake_bp` | `` | Intake form, approval/rejection flow |
| `internal_bp` | `/internal` | Cron-triggered lifecycle execution (shared secret auth) |
| `webhooks_bp` | `/api/webhooks` | Postmark inbound email → inventory record |
| `inventory_bp` | `/inventory` | Full inventory CRUD + scanner + photo upload |
| `health_bp` | `` | `/healthz`, `/readyz` for Cloud Run probes |
| `help_bp` | `/help` | Static help docs |

---

## Security Boundaries

| Concern | Implementation |
|---|---|
| Authentication | Session cookie (`fsi_user_id`); `@login_required` returns 401 |
| CSRF | Flask-WTF `CSRFProtect`; `X-CSRFToken` meta tag for AJAX |
| Webhook auth | `X-Postmark-Token` header vs `POSTMARK_WEBHOOK_TOKEN` env |
| Internal cron | `X-FSI-Internal-Secret` header vs `INTERNAL_CRON_SHARED_SECRET` env |
| Rate limiting | Flask-Limiter (disabled in `APP_ENV=test`) |
| Session cookies | `Secure`, `HttpOnly`, `SameSite=Lax`; `Secure` enforced in production |
| DB isolation | Alembic `include_name` filter prevents migrations touching `users` |

---

## Shared Database Schema Ownership

Lifecycle and expenses share the same Cloud SQL PostgreSQL instance. Schema ownership is enforced at the application and migration level.

| Table | Owner app | Lifecycle can |
|---|---|---|
| `users` | expenses | SELECT only |
| `intake_request` | lifecycle | Full DDL + DML |
| `inventory` | lifecycle | Full DDL + DML |
| `asset_categories` | lifecycle | Full DDL + DML |
| `role_matrix` | lifecycle | Full DDL + DML |
| `question_matrix` | lifecycle | Full DDL + DML |
| `action_matrix` | lifecycle | Full DDL + DML |
| `communication_options` | lifecycle | Full DDL + DML |

The `migrations/env.py` `include_name` function returns `False` for any table not in `LIFECYCLE_OWNED_TABLES`, ensuring `flask db migrate` autogenerate never produces DDL for expenses-owned tables.
