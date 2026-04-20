# FSI Application Ecosystem Overview

> **This is the canonical ecosystem reference.** Each FSI repository contains a slim pointer file (`FSI_ECOSYSTEM.md`) that links back here.
> When a dedicated `kdnye/fsi-docs` repository is created, this document will migrate there.

---

## 1. Application Portfolio

| App | Repo | Status | Primary Users | Stack |
|-----|------|--------|---------------|-------|
| **Expenses** | `kdnye/expenses` | Live (primary) | All employees — expense reporting and approval | Flask, PostgreSQL, GCS |
| **FSI POD** | `kdnye/fsi_pod` | Launching soon | Drivers, ops team — proof of delivery capture | Flask, PostgreSQL, GCS |
| **Lifecycle** | `kdnye/lifecycle` | In testing | HR/admin — employee onboarding and offboarding | Flask, PostgreSQL, Postmark |
| **Driver Paperwork** | `kdnye/driver-paperwork` | In development | Drivers, ops — driver document management | Flask, PostgreSQL, Couchdrop |
| **Motive Dashboard** | `kdnye/motive-dashboard` | Launching soon | Ops managers — real-time fleet monitoring | Streamlit, Cloud Functions, PostgreSQL |
| **Smart Trucks** | `kdnye/smart-trucks` | In development | Hardware/ops — edge GPS/BLE/power telematics | Python containers, Balena, SQLite (edge) + PostgreSQL (cloud sync) |
| **IT Inventory** | *(planned)* | Not started | IT team — hardware and software asset tracking | TBD (FSI standard) |
| **Hard Asset Tracking** | *(planned)* | Not started | Ops — physical asset lifecycle management | TBD (FSI standard) |

---

## 2. Shared Database

All 6 deployed applications connect to a **single shared GCP Cloud SQL PostgreSQL instance**.

### Schema Ownership

Schema ownership determines who may run structural migrations (`ALTER TABLE`, `DROP COLUMN`, `DROP TABLE`) on a given table group. All other apps may only `SELECT` or `INSERT` on tables they do not own.

| Table Group | Owner Repo | Consumers |
|-------------|------------|-----------|
| `users` (identity) | `kdnye/expenses` | lifecycle, fsi_pod, driver-paperwork, motive-dashboard |
| `expense_reports`, `expense_items` | `kdnye/expenses` | — |
| `shipments`, `shipment_legs`, `pod_records`, `shipment_leg_transitions` | `kdnye/fsi_pod` | motive-dashboard (read) |
| `driver_documents` and related | `kdnye/driver-paperwork` | — |
| `fleet_status_monitor`, `geofence_dwell_history`, `geofence_aliases`, event tables | `kdnye/motive-dashboard` | smart-trucks (write-only producer) |
| `employees`, `onboarding_requests`, `offboarding_requests` | `kdnye/lifecycle` | — |

### Migration Discipline

- **Structural changes to shared tables** (especially `users`) must originate from the owner repo and be reviewed for downstream impact before deployment.
- **Secondary apps** that map shared tables (e.g., lifecycle and fsi_pod mapping `users`) must declare those mappings read-only and must not include destructive migration operations targeting those tables.
- All migrations use **Alembic** (`alembic upgrade head` / `flask db upgrade`). Legacy `.sql` files are deprecated.

---

## 3. Cross-App Data Flows

```
lifecycle  ──→  users table  ──→  expenses / fsi_pod / driver-paperwork / motive-dashboard
                                  (identity consumed at login + display)

smart-trucks  ──→  telematics tables  ──→  motive-dashboard
              (edge GPS/BLE/power sync)    (fleet map + geofence display)

fsi_pod  ──→  shipment/POD data  ──→  motive-dashboard
         (delivery state machine)     (shipment status on fleet map)
```

Planned future flows:
- `lifecycle` → `IT inventory` (provision hardware asset on new employee onboard)
- `lifecycle` → `hard asset tracking` (assign vehicle/equipment on driver onboard)

---

## 4. Architectural Patterns

### Standard (Flask apps)

`expenses`, `lifecycle`, `fsi_pod`, `driver-paperwork` all follow the [FSI Application Architecture Standard](./FSI%20Application%20Architecture%20Standard:%20Technical%20Governance%20Handbook).

Core rules (summary):
- Flask + SQLAlchemy + PostgreSQL + Gunicorn + Cloud Run
- `/app`, `/services`, `/templates`, `wsgi.py` directory structure
- Model Constant Rule (`*_TABLE` constants in `models.py`)
- Alembic-only migrations
- Postmark for all transactional email (no SMTP)
- GCS or equivalent for file storage (ADC auth preferred; `driver-paperwork` uses Couchdrop + `GCS_TOKEN`)
- Fail-fast on missing `SECRET_KEY` / `DATABASE_URL` in production
- Roboto + Bebas Neue typography with Google Fonts preconnect

### Approved Exceptions

| Repo | Exception | Rationale |
|------|-----------|----------|
| `motive-dashboard` | Streamlit + GCP Cloud Functions + Pub/Sub | Real-time fleet monitoring requires event-driven webhook ingest (Motive API). Streamlit enables rapid multi-page dashboard iteration without Flask template overhead. Formally approved. |
| `smart-trucks` | Python containers on Balena (Raspberry Pi), SQLite WAL, no web framework | Edge device with intermittent connectivity. Requires local store-and-forward durability, OTA updates, and hardware I/O (UART GPS, I2C IMU, BLE). Not a web application. |

---

## 5. Future Apps (Planned)

### IT Inventory
- **Purpose**: Track hardware assets (laptops, monitors, phones, peripherals) assigned to employees.
- **Integration point**: `lifecycle` triggers provisioning on onboard; `lifecycle` triggers return workflow on offboard.
- **Shared DB**: Will consume `users` table (read-only); owns its own `assets`, `asset_assignments` tables.
- **Expected stack**: FSI standard (Flask + PostgreSQL + Cloud Run).

### Hard Asset Tracking
- **Purpose**: Physical asset lifecycle management (trucks, trailers, equipment).
- **Integration point**: `motive-dashboard` provides telematics context; `lifecycle` assigns on driver onboard.
- **Shared DB**: Will consume telematics tables (read-only); owns its own `hard_assets` tables.
- **Expected stack**: FSI standard (Flask + PostgreSQL + Cloud Run).

---

## 6. Full Governance Reference

For complete technical standards covering migrations, deployment, email, secrets, and UI/branding:

→ **[FSI Application Architecture Standard: Technical Governance Handbook](./FSI%20Application%20Architecture%20Standard:%20Technical%20Governance%20Handbook)** (this repo)
