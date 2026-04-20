# AI Agent Instructions for Employee Lifecycle App

This file provides architectural context and strict coding guidelines for the Freight Services Inc. (FSI) Employee Lifecycle application [2]. When generating, refactoring, or reviewing code in this repository, you must adhere to the FSI Technical Governance Standard [3].

See also: [FSI_ECOSYSTEM.md](./FSI_ECOSYSTEM.md) for the full app portfolio and shared DB schema map.

## 1. Project Overview
This application is a centralized onboarding and offboarding rules engine that automates MSP ticket creation (Stellar Support, Stellar Sales, BlackPoint) [2]. 
The core logic relies on a **tripartite matrix structure**:
*   **Role Matrix:** Baseline entitlements (hardware, access) based on employment profile [4].
*   **Question Matrix:** Conditional UI branching to prevent form fatigue [5].
*   **Action Matrix:** Automated execution mapping intake data to vendor-specific API payloads [5, 6].

## 2. Tech Stack & Directory Structure
*   **Core Stack:** Python 3.10+, Flask (Blueprints), SQLAlchemy, PostgreSQL [7].
*   **Deployment:** Google Cloud Run via Docker and Cloud Build (`cloudbuild.yaml`) [8].
*   **Directory Layout:** 
    *   `/app`: Core logic, blueprint registration, and models [9].
    *   `/services`: **Mandatory location for all business logic and third-party integrations.** Never place business logic directly in route handlers [9].
    *   `/templates`: Jinja2 templates [10].
    *   `wsgi.py`: Production entrypoint [9].

## 3. Strict Architectural Rules

### Database & ORM Mandates
*   **The Model Constant Rule:** Every new database table must be registered as a module-level constant in `app/models.py` using the exact format `<TABLE_NAME_UPPER>_TABLE = "table_name"` before it is referenced in SQLAlchemy models [11-13].
*   **Alembic Migrations Only:** Never execute or generate raw `.sql` files for schema rollouts [11, 12]. Use `alembic upgrade head` or `flask db upgrade` exclusively [14].
*   **Health Checks:** The `/readyz` or `/healthz` endpoints must return a `503` status with actionable guidance (listing missing columns/tables) if the schema is out of sync [14, 15].

### Email & Communication Mandates
*   **Postmark Only:** All transactional emails must use the Postmark API. SMTP is strictly prohibited [16].
*   **No Hardcoded Emails:** Email bodies must never be hardcoded in Python [17]. Templates are managed in the Postmark UI.
*   **Template Dictionary:** To trigger emails, construct a `template_model` Python dictionary containing the dynamic variables (e.g., `{{employee_name}}`) and push it to the `app/services/email.py` (or `mail.py`) layer [17, 18].

### Production & Deployment Constraints
*   **Gunicorn Entrypoint:** The production startup command is `gunicorn --bind 0.0.0.0:${PORT} wsgi:app`. **Do not add the `--factory` flag** to this command [19, 20].
*   **Fail-Fast Security:** If `SECRET_KEY` or `DATABASE_URL` are missing or malformed when `FSI_PRODUCTION=true`, the application must immediately enter Maintenance Mode or refuse to start. Never fall back to an ephemeral key in production [21, 22].

### Frontend UI & Branding
*   **FSI Font Strategy:** Templates must include preconnect hints for `fonts.googleapis.com` and `fonts.gstatic.com` in `base.html` [23, 24].
*   **Typography:** Use **Roboto** for body copy and UI controls, and **Bebas Neue** for display headings using the `.fsi-display` class [23, 24]. 
*   **CSS Fallbacks:** Always maintain the resilient fallback stack `system-ui, sans-serif` [23, 24].

## 4. Lifecycle App Specific Directives for AI Agents
1. **Email Templating Strict Prohibition:** NEVER write HTML email bodies in Python files. Email rendering is managed in Postmark templates. Use service-layer template sends with a `template_model` dictionary.
2. **Shared Schema Awareness:** This app shares PostgreSQL identity data with FSI EXPENSES. Do not alter `User` model structure or shared-table assumptions unless explicitly requested.
3. **Migration Auditing Requirement:** If instructing `flask db migrate`, explicitly remind reviewers to inspect generated revisions and remove destructive shared-table operations (for example, any `drop_column` or `drop_table` targeting `users`) before `flask db upgrade`.

## 5. Ecosystem Context

This application is part of the FSI shared infrastructure ecosystem. See [FSI_ECOSYSTEM.md](./FSI_ECOSYSTEM.md) for the full app portfolio and cross-app data flows.

**Shared DB role:** Secondary consumer of `users` (owned by `kdnye/expenses`). This app owns onboarding/offboarding/lifecycle tables.

**Schema ownership rule:** Never run structural migrations against `users`. Review all generated Alembic revisions for destructive operations on shared tables before applying.

**Identity data flow:** Lifecycle creates and onboards employee records that are consumed downstream by expenses, fsi_pod, driver-paperwork, and motive-dashboard for identity lookup and access.

**Future integrations:** When the IT Inventory and Hard Asset Tracking apps are created, Lifecycle will trigger provisioning events to those apps on employee onboard/offboard.

**Governance:** The [FSI Application Architecture Standard](./FSI%20Application%20Architecture%20Standard:%20Technical%20Governance%20Handbook) is maintained in this repository as the canonical reference for all FSI apps.
