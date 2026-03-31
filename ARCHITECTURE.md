# Employee Lifecycle App Architecture

This document defines how the Freight Services Inc. (FSI) Employee Lifecycle application works today, where it is going, and which design rules are non-negotiable.

---

## 1) Purpose and Scope

The Lifecycle application is FSI’s centralized onboarding and offboarding rules engine. It replaces fragmented, manual MSP communications with a single intake workflow that drives consistent ticket creation for:

- Stellar Support
- Stellar Sales
- BlackPoint

The platform is organized around a **tripartite matrix model**:

1. **Role Matrix** — baseline entitlements by employment profile.
2. **Question Matrix** — conditional intake logic to reduce form fatigue.
3. **Action Matrix** — deterministic mapping from intake data to execution payloads.

---

## 2) Current State (As-Is)

### 2.1 Business Workflow

- Onboarding/offboarding requests are captured through a centralized intake flow.
- Role profiles determine default access, hardware, and communication entitlements.
- Conditional question paths are used to ask only context-relevant fields.
- Resulting actions are dispatched as MSP-facing tasks/tickets.

### 2.2 Core Matrix Behavior

#### Role Matrix (Baseline Entitlements)

| Role Profile | M365 Account | Hardware Provisioning | Internal Network / VPN | Comm Systems | Specific Access |
|---|---|---|---|---|---|
| Driver | Yes (Basic/F1) | No (Personal Device) | No | Optional Mobile | N/A |
| Office/Ops | Yes (Standard/E3) | Laptop, Dock, Monitors | Yes (Local/Shares) | Optional Desk/Softphone | Dept DLs, Receptionist |
| Manager | Yes (Standard/E3) | Laptop, Dock, Monitors | Yes (VPN Required) | Yes (Direct + Ext) | Elevated Approvals |
| Warehouse | Yes (Shared/Kiosk) | Shared Workstation | Internal Only | Shared Area Phone | Warehouse Systems |
| Contractor | Yes (Restricted) | No (BYOD) | Restricted VPN | No | Enforced Expiration |

#### Question Matrix (Dynamic Intake)

- **Global fields**: legal name, preferred name, start date, manager, location, role profile.
- **Office/Manager branch**: non-standard hardware, DLs, shared mailboxes, external phone number.
- **Driver branch**: mobile dispatch access.
- **Contractor branch**: mandatory contract end date (hard stop).
- **Offboarding branch**: immediate vs scheduled exit; mailbox conversion/forwarding.

#### Action Matrix (Execution Routing)

- **Account creation**: route M365 requests to Stellar Support.
- **Hardware procurement**: route specs/shipping to Stellar Sales.
- **Telecom provisioning**: route extension/DID requests to BlackPoint.
- **Immediate offboarding**: trigger high-priority disablement workflow.

### 2.3 Technical Baseline

- **Language**: Python (3.10+ target).
- **Framework**: Flask with Blueprints.
- **ORM/DB**: SQLAlchemy + PostgreSQL.
- **Migrations**: Alembic via Flask-Migrate.
- **Runtime**: Gunicorn (`wsgi:app`).
- **Deployment**: Docker + Google Cloud Run + Cloud Build.
- **UI**: Jinja2 templates with FSI typography standards.

### 2.4 Current Integration Posture

- Transactional notifications/ticket communications are sent via **Postmark**.
- Identity data uses a **shared users table pattern** aligned with other FSI systems.
- Health checks are expected to verify DB/schema readiness before traffic acceptance.

---

## 3) Future State (To-Be)

### 3.1 Product and Workflow Evolution

- Expand from centralized intake to **full orchestration**, including status lifecycle visibility.
- Add richer automation around fulfillment sequencing and SLA-aware offboarding priorities.
- Strengthen policy-driven intake so role/question/action matrices are easier to govern and evolve.

### 3.2 Platform Maturity Goals

- Increase automation confidence with stricter schema-readiness and fail-fast controls.
- Improve internal operability (clearer health diagnostics, safer migrations, auditable change flow).
- Continue alignment with Microsoft 365 identity workflows and SSO expectations.

### 3.3 Implementation Phases

| Phase | Focus | Deliverables |
|---|---|---|
| Phase 1: Foundation | Central Intake | Role matrix, core intake form, generated ticket payload drafts |
| Phase 2: Automation | Task Orchestration | Auto task generation, status dashboard, Postmark template sends |
| Phase 3: Optimization | Full Integration | Guided wizard UX, Microsoft SSO/user sync, deeper MSP API hooks |

---

## 4) Design Absolutes (Non-Negotiable)

These rules are mandatory and must be enforced in implementation and review.

### 4.1 Architecture and Layering

1. **Service-layer rule**: business logic and external integrations belong in `/services` (or `app/services`), not route handlers.
2. **Tripartite model rule**: role/question/action matrix responsibilities must remain logically separated.
3. **Production entrypoint rule**: use `gunicorn --bind 0.0.0.0:${PORT} wsgi:app` (no `--factory`).

### 4.2 Database and Migration Governance

1. **Model constant rule**: every new table is declared as a module-level constant in `app/models.py` using `<TABLE_NAME_UPPER>_TABLE = "table_name"` before model use.
2. **Alembic-only rollout rule**: no raw `.sql` schema rollout process; use `alembic upgrade head` or `flask db upgrade`.
3. **Shared identity protection rule**: do not ship destructive shared-table changes (`drop_column`, `drop_table`, etc.) targeting `users`.
4. **Readiness correctness rule**: `/readyz` or `/healthz` must return `503` with actionable missing schema details when out of sync.

### 4.3 Email and Communication Governance

1. **Postmark-only rule**: all transactional email/ticket messaging uses Postmark API.
2. **No inline email HTML rule**: Python code must not hardcode rendered email bodies.
3. **Template model rule**: sends must pass dynamic data through a `template_model` dictionary to the email service layer.

### 4.4 Security and Reliability

1. **Fail-fast production config rule**: with `FSI_PRODUCTION=true`, invalid/missing `SECRET_KEY` or `DATABASE_URL` must force maintenance mode or startup failure.
2. **No ephemeral production secrets rule**: never fall back to generated runtime secrets in production.
3. **Secrets management rule**: production secrets (including `POSTMARK_SERVER_TOKEN`) must come from managed secret storage.

### 4.5 UI and Brand Consistency

1. **Font preconnect rule**: templates must include preconnect hints for `fonts.googleapis.com` and `fonts.gstatic.com` in base layout.
2. **Typography rule**: use Roboto for body/UI controls and Bebas Neue for display headings (`.fsi-display`).
3. **Fallback stack rule**: keep `system-ui, sans-serif` fallback stack intact.

---

## 5) Shared Identity Database Pattern

The Lifecycle app participates in a shared identity model and does not own an independent identity schema.

- `users` table remains a shared contract across FSI applications.
- Lifecycle-driven migrations require manual review to avoid cross-application breakage.
- Provisioning should commit identity changes before external notification dispatch to prevent inconsistent side effects.

---

## 6) Operational Checklist (Implementation Guardrails)

Use this checklist during development and review:

- [ ] Business logic implemented in service layer, not route handlers.
- [ ] New tables added with `*_TABLE` constants in `app/models.py`.
- [ ] Migration revisions reviewed for destructive changes on shared tables.
- [ ] Health endpoint validates schema readiness and emits actionable 503 responses.
- [ ] Email flows use Postmark templates with `template_model` payloads.
- [ ] Production startup uses approved Gunicorn command.
- [ ] `SECRET_KEY`/`DATABASE_URL` fail-fast behavior verified for production mode.
- [ ] Typography/font preconnect requirements preserved in base template.

---

## 7) Summary

The architecture is intentionally governance-first: centralized lifecycle intake, matrix-driven rules, service-layer execution, and strict controls around shared identity data and production reliability. The near-term roadmap deepens automation and observability while preserving these design absolutes.
