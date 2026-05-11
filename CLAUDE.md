# CLAUDE.md — FSI Lifecycle

Lifecycle-specific rules for AI-assisted development. Always read this before making changes.

---

## Schema Ownership

| Table | Owner | Lifecycle access |
|---|---|---|
| `users` | `kdnye/expenses` | **Read-only** — never ALTER or DROP |
| `role_matrix` | lifecycle | Read/Write |
| `question_matrix` | lifecycle | Read/Write |
| `action_matrix` | lifecycle | Read/Write |
| `intake_request` | lifecycle | Read/Write |
| `inventory` | lifecycle | Read/Write |
| `asset_categories` | lifecycle | Read/Write |
| `communication_options` | lifecycle | Read/Write |
| `alembic_version` | lifecycle | Read/Write |

**Critical:** `migrations/env.py` contains an `include_name` filter that prevents Alembic autogenerate from emitting DDL statements for `users`. Never remove or weaken this filter. After `flask db migrate`, verify the generated script contains no `DROP` or `ALTER` statements targeting `users`.

---

## Auth Pattern

- Session-based via `app/auth_utils.py` — **not Flask-Login**.
- Session key: `fsi_user_id` (constant `SESSION_USER_ID_KEY`).
- Decorator: `@login_required` from `app.auth_utils` (returns 401 on unauthenticated access).
- User loaded from `users` table per request in `attach_current_user` (`app.before_request`).
- Available as `g.current_user` in templates and view functions.

---

## Service Layer

- All business logic lives in `app/services/`. The root `services/` directory is **deprecated** — keep it only for backward compat but do not add new files there.
- Import services as: `from app.services import inventory_service` or `from app.services.email import send_templated_email`.
- GCS photo operations: `app/services/asset_storage.py` (uses Application Default Credentials).
- Inventory CRUD: `app/services/inventory_service.py`.
- Email dispatch: `app/services/email.py` (respects `MAIL_SUPPRESS_SEND` env var).

---

## Blueprint Layout

```
app/blueprints/<feature>/__init__.py   # empty
app/blueprints/<feature>/routes.py    # Blueprint definition + routes
```

- Do NOT set `template_folder` on blueprints. Templates resolve from the app-level `templates/` directory.
- Register blueprints in `app/__init__.py` inside `create_app()`.
- Existing blueprints in `app/routes/` are legacy; new features use `app/blueprints/`.

---

## Inventory Module

- Blueprint: `inventory_bp` registered at `/inventory` prefix.
- Service: `app/services/inventory_service.py` handles all CRUD.
- GCS photos: `ASSET_PHOTOS_BUCKET` env var **required** for photo upload; raises `RuntimeError` if unset.
- Status enum: `AssetStatus` (Available, Assigned, In_Repair, Retired, Lost) — PostgreSQL native enum `asset_status`.
- Scanner JS: `app/static/js/asset_scanner.js` — camera via html5-qrcode CDN, BLE via Web Bluetooth API (Chrome/Edge + HTTPS only).
- Scan AJAX endpoint: `POST /inventory/scan` accepts JSON `{tag: string}`, returns `{found, id, detail_url, ...}`.

---

## Theme Persistence

Lifecycle **cannot** add a `theme` column to the `users` table (owned by expenses). Theme is stored in `localStorage['fsiTheme']` only. The `POST /account/theme` endpoint is a no-op that returns 200 to keep the JS pattern consistent with the FSI standard.

---

## CSRF

- Flask-WTF `CSRFProtect` is active in all environments except `APP_ENV=test`.
- `webhooks_bp` and `internal_bp` are CSRF-exempt (they use their own auth headers).
- AJAX requests must include `X-CSRFToken` header (read from `<meta name="csrf-token">`).
- Traditional form POSTs must include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />`.

---

## Alembic Rules

1. Always use `flask db migrate` + review the generated script before applying.
2. The `include_name` filter in `migrations/env.py` must never be removed.
3. After any `flask db migrate`, grep the generated file for `users` and verify it contains no DDL.
4. PostgreSQL enums must be created with `checkfirst=True` before columns that use them.
5. Use `MIGRATE_ON_STARTUP=true` on Cloud Run so migrations run before requests are served.

---

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

- `APP_ENV=test` is set by `required_test_env` autouse fixture — disables CSRF and rate limiting.
- `DATABASE_URL=sqlite:///:memory:` in tests — never connect to Cloud SQL from test suite.
- `MAIL_SUPPRESS_SEND=true` in tests — no emails sent.
- Use `app`, `client`, `create_user`, `logged_in_client` fixtures from `tests/conftest.py`.
