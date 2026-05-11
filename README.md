# FSI Lifecycle

Employee lifecycle automation engine for Freight Services Inc. Handles onboarding and offboarding intake, manager approval routing, and automated dispatches to IT vendors (Stellar Support/Sales) and internal ops. Includes a full inventory management system for tracking company assets.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set required env vars (see table below)
export DATABASE_URL="postgresql+pg8000://user:pass@/dbname?unix_sock=/cloudsql/..."
export SECRET_KEY="your-secret-key"
export POSTMARK_SERVER_TOKEN="your-postmark-token"

# Run migrations
flask db upgrade

# Seed baseline data
python scripts/seeds.py

# Start dev server
flask run
```

## Architecture

- **Framework:** Flask 3.x with Blueprint architecture
- **Database:** Cloud SQL PostgreSQL (shared with `kdnye/expenses`; lifecycle owns all tables except `users`)
- **Email:** Postmark API (no SMTP)
- **Storage:** Google Cloud Storage (asset photos)
- **Auth:** Session-based (`fsi_user_id` cookie); no Flask-Login
- **Migrations:** Flask-Migrate / Alembic with `include_name` filter protecting the `users` table
- **Design:** Bootstrap 5.3.3 + FSI design tokens (CSS custom properties), dual dark mode

See [`docs/architecture.md`](docs/architecture.md) for the full system diagram.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes (prod) | — | Flask session signing key. Load from Secret Manager. |
| `DATABASE_URL` | Yes (prod) | `sqlite:///lifecycle.db` | PostgreSQL connection string. |
| `POSTMARK_SERVER_TOKEN` | Yes (prod) | — | Postmark Server API token for transactional email. |
| `POSTMARK_WEBHOOK_TOKEN` | Recommended | — | Token for authenticating Postmark inbound webhooks. |
| `ASSET_PHOTOS_BUCKET` | For photo upload | — | GCS bucket name for asset photos. |
| `MAIL_SUPPRESS_SEND` | No | `false` | Set `true` in dev to skip email sending. |
| `MIGRATE_ON_STARTUP` | No | `false` | Leave `false` in Cloud Run. Use CI/CD or startup command to run `flask db upgrade` once before Gunicorn workers boot. |
| `DB_POOL_RECYCLE` | No | `1800` | SQLAlchemy `pool_recycle` (seconds). |
| `DB_POOL_MAX_OVERFLOW` | No | `5` | SQLAlchemy `max_overflow`. |
| `APP_ENV` | No | `development` | Set `test` to disable CSRF and rate limiting. |
| `FSI_PRODUCTION` | No | auto-detected | Set `true` to enforce production validations. |
| `HR_CC_EMAILS` | No | FSI defaults | Comma-separated CC list for intake notifications. |
| `FSI_OPS_EMAIL` | No | `ops@freightservices.net` | Ops team email for driver provisioning. |
| `INTERNAL_CRON_SHARED_SECRET` | No | — | Secret for `X-FSI-Internal-Secret` cron auth header. |

## Database

Lifecycle shares a Cloud SQL instance with `kdnye/expenses`. **Never modify the `users` table from lifecycle migrations.** The Alembic `include_name` filter in `migrations/env.py` enforces this automatically.

```bash
# Create a new migration after model changes
flask db migrate -m "description"

# Always review the generated file before applying!
flask db upgrade

# Seed baseline policy rows and asset categories
python scripts/seeds.py
```

## Inventory Module

Full asset lifecycle management at `/inventory`:

- **CRUD:** List, detail, create, edit, archive assets
- **Categories:** Customizable hierarchy (Computers → Laptops, Vehicles → Trucks, etc.)
- **Photos:** Upload to GCS (`ASSET_PHOTOS_BUCKET` required)
- **Scanner:** Barcode/QR via camera (html5-qrcode) + BLE tags (Web Bluetooth — Chrome/Edge + HTTPS)
- **Status tracking:** Available, Assigned, In_Repair, Retired, Lost
- **Email intake:** Postmark inbound webhook at `POST /api/webhooks/postmark-inbound` parses serial numbers from email bodies

## Tests

```bash
pytest
pytest --cov=app tests/
```

Tests use SQLite in-memory DB. No network connections to Cloud SQL or Postmark are made during tests. GCS calls are mocked in `tests/test_asset_storage.py`.

## Deployment

Deployed as a Cloud Run service. On each deploy:

1. Docker image built from `Dockerfile`
2. Cloud Run service updated
3. Container startup runs `flask db upgrade` before Gunicorn boots workers.
4. `/healthz` and `/readyz` endpoints are available for Cloud Run health probes

Cloud Run provides `K_SERVICE` env var which lifecycle uses to auto-detect production mode (`FSI_PRODUCTION=true`).
