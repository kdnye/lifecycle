# Employee Lifecycle Automation Engine

A centralized onboarding/offboarding rules engine for Freight Services Inc. (FSI) that replaces fragmented manual MSP requests with structured, auditable workflow execution.

---

## Executive Summary

FSI is migrating from decentralized ticket-by-email operations to a matrix-driven lifecycle platform that:

- standardizes identity, hardware, and access provisioning,
- transforms intake intent into structured payloads,
- and enforces governance/security controls as design-time requirements (not optional conventions).

This repository documents **where the platform is today**, **where it is going**, and the **design absolutes** that cannot be violated.

---

## Current State (Phases 1–2)

### What is active now

- **Dynamic Intake UI** via `POST /preview-actions` for role/event-specific action recommendations.
- **Tripartite rules engine data model** persisted in PostgreSQL:
  - `RoleMatrix`
  - `QuestionMatrix`
  - `ActionMatrix`
- **Shared identity auto-provisioning** to the shared `users` table during onboarding.
- **Automated MSP ticketing through Postmark** for onboarding-related workflows.
- **Integrated help center templates** for entitlement and routing guidance.

### Operational reality

- Core onboarding automation is live.
- Offboarding execution is still partial: offboarding requests are currently flagged as pending in the processing flow.

---

## Future State (Phase 3 Target)

### Planned capabilities

- **Full offboarding execution**
  - immediate revocation and disablement workflows,
  - scheduled termination handling,
  - mailbox forwarding/conversion policy automation.
- **Direct ITSM/PSA API integrations**
  - migration from email-first handoff toward direct vendor API execution.
- **Manager approval gates**
  - stateful approvals before outbound task dispatch.
- **Microsoft Entra ID lifecycle sync**
  - deeper SSO and identity lifecycle automation.

### End-state objective

A single auditable lifecycle control plane where request intent, entitlement logic, and downstream execution are all governed by explicit matrix policy.

---

## Design Absolutes (Non-Negotiable)

### 1) Architecture Absolutes

- **Service-layer isolation is mandatory**
  - Business logic and third-party integration code must live in `/services`.
  - Route handlers must orchestrate only; they must not contain business logic.
- **Tripartite matrix is the source of truth**
  - Role defaults, intake branching, and execution mapping are independent but coordinated layers.

### 2) Database & Schema Absolutes

- **Model Constant Rule**
  - Every table must be declared as a module-level constant in `app/models.py` before SQLAlchemy model usage.
  - Format: `<TABLE_NAME_UPPER>_TABLE = "table_name"`.
- **Alembic-only migrations**
  - No raw schema SQL rollouts.
  - Use `alembic upgrade head` or `flask db upgrade`.
- **Schema health checks must fail loudly**
  - `/readyz` and/or `/healthz` must return `503` with actionable missing schema details when out of sync.

### 3) Email & Communication Absolutes

- **Postmark-only for transactional mail**
  - SMTP is prohibited.
- **No hardcoded HTML email bodies in Python**
  - Email content is managed in Postmark templates.
- **Template-model contract is required**
  - Dynamic values must be passed via a Python `template_model` dictionary in the service layer.

### 4) Security & Runtime Absolutes

- **Fail-fast production boot**
  - If `FSI_PRODUCTION=true` and `SECRET_KEY` or `DATABASE_URL` is missing/malformed, the app must refuse startup or enter maintenance mode.
- **No silent insecure fallback in production**
  - Ephemeral/default secret behavior is forbidden in production mode.

### 5) Deployment Absolutes

- **Canonical production command**
  - `gunicorn --bind 0.0.0.0:${PORT} wsgi:app`
- **Gunicorn `--factory` flag is prohibited**
  - Do not add or rely on `--factory`.

### 6) UI/Branding Absolutes

- **Font loading requirements in `base.html`**
  - Include preconnect hints for `fonts.googleapis.com` and `fonts.gstatic.com`.
- **Typography requirements**
  - Roboto for body/UI,
  - Bebas Neue for display headings via `.fsi-display`.
- **Fallback stack required**
  - Always retain `system-ui, sans-serif` fallback behavior.

---

## Core System Model: Tripartite Matrix

### Role Matrix (baseline entitlements)

| Role Profile | M365 Account | Hardware | Network / VPN | Comms | Specific Access |
|---|---|---|---|---|---|
| Driver | Yes (Basic/F1) | No (Personal Device) | No | Optional Mobile | N/A |
| Office/Ops | Yes (Standard/E3) | Laptop, Dock, Monitors | Yes (Local/Shares) | Optional Desk/Softphone | Dept DLs, Receptionist System |
| Manager | Yes (Standard/E3) | Laptop, Dock, Monitors | Yes (VPN Required) | Yes (Direct + Ext) | Elevated Approvals, Management DLs |
| Warehouse | Yes (Shared/Kiosk) | Shared Workstation | Internal Only | Shared Area Phone | Warehouse Systems |
| Contractor | Yes (Restricted) | No (BYOD) | VPN (Restricted) | No | Enforced Expiration |

### Question Matrix (conditional intake)

- **Office/Manager branch**: non-standard hardware, DLs/shared mailboxes, receptionist access.
- **Driver branch**: mobile dispatch requirements only.
- **Contractor branch**: hard-stop contract end date.
- **Offboarding branch**: immediate vs. scheduled termination and mailbox handling.

### Action Matrix (execution routing)

| Intake Condition | Automated Action | Target Vendor/System |
|---|---|---|
| New Hire + M365 | Generate first.last@freightservices.net account request | Stellar Support |
| New Hire + Hardware | Generate hardware ticket with shipping/model details | Stellar Sales |
| Phone/Extension Required | Map user to extension/DID telecom ticket | BlackPoint |
| Immediate Offboard | Priority revocation (AD, M365 sessions, VPN) | Stellar Support |
| Office/Manager Hire | Trigger receptionist entry webhook | Google Sheet API |

---

## Technology Baseline

- **Language:** Python 3.10+
- **Framework:** Flask (Blueprint-oriented)
- **ORM:** SQLAlchemy + PostgreSQL
- **Production Runtime:** Gunicorn (WSGI)
- **Deployment:** Google Cloud Run + Cloud Build

### Standard repository layout

```text
/app
  /services      # Business logic and integrations
  /templates     # Jinja2 templates by module
  auth.py
  models.py
  config.py
/migrations      # Alembic revisions
wsgi.py          # Production entrypoint
```

---

## Delivery & Operations

### CI/CD expectations (`cloudbuild.yaml`)

1. Build and push container to Artifact Registry.
2. Run blocking migrations (`flask db upgrade`).
3. Deploy to Cloud Run with secrets mounted.

### Required secrets/environment

- `APP_ENV`
- `FSI_PRODUCTION`
- `DATABASE_URL`
- `INSTANCE_CONNECTION_NAME` (Cloud Run/Unix socket path source)
- `SECRET_KEY`
- `POSTMARK_SERVER_TOKEN`
- `DEFAULT_SENDER_EMAIL`
- `MAIL_MESSAGE_STREAM`
- `HR_CC_EMAILS`
- `FSI_OPS_EMAIL`
- `STELLAR_SUPPORT_EMAIL`
- `STELLAR_SALES_EMAIL`

### Cloud SQL wiring (production)

For this deployment, the Cloud SQL instance must be:

- `quote-tool-483716:us-central1:quote-postgre`

Ensure both of these are set during deploy:

1. Cloud Run instance attachment: `--add-cloudsql-instances=quote-tool-483716:us-central1:quote-postgre`
2. Runtime env var: `INSTANCE_CONNECTION_NAME=quote-tool-483716:us-central1:quote-postgre`

If either is mismatched (for example using `quotetool-postgres-instance`), routes that query the database can return 500 errors due to unreachable Unix socket paths.

### Notification routing notes

- All transactional lifecycle notifications are sent through Postmark templates via the service layer (`services/email.py` and `services/workflow.py`).
- Vendor and operations routing addresses are configured through environment variables, not hardcoded in route handlers.
- `DEFAULT_SENDER_EMAIL` is the canonical sender env var; `MAIL_DEFAULT_SENDER` is no longer used by the application config.

---

## Migration Roadmap (Reference)

| Phase | Focus | Deliverables |
|---|---|---|
| 1: Foundation | Central Intake | Role matrix, intake form, draft email generation for manual review |
| 2: Automation | Task Orchestration | Automatic task generation, status dashboard, Postmark integration |
| 3: Optimization | Full Integration | Guided wizard UX, Entra sync, direct MSP API hooks |

---

## Implementation Notes for Contributors

- Keep business logic in service modules.
- Preserve shared-table assumptions for `users` unless explicitly approved.
- Review generated Alembic revisions before upgrade, especially for any destructive shared-table operations.
- Maintain Postmark template-driven email flows; do not inline HTML email content in Python.
