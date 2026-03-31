Employee Lifecycle Automation Engine & Migration Strategy

1. Project Vision and Strategic Objectives

This document defines the strategic migration from a decentralized, manual Managed Service Provider (MSP) request model to a unified, automated rules engine. Currently, Freight Services Inc. (FSI) operations are hindered by "email drift"—a fragmented landscape of manual communications that leads to inconsistent provisioning and security gaps. By implementing this engine, we are fundamentally decoupling intent from execution. This shift ensures that operational velocity is no longer bottlenecked by human memory or manual ticket entry, but is driven by mathematical precision and structured payloads.

The core mission is anchored by three primary objectives:

* Consolidation of Identity, Hardware, and Access Workflows: Unifying disparate request paths for M365, physical equipment, and network permissions into a single logical stream.
* Transformation of Manual Intent into Structured API/Email Payloads: Transitioning from hand-written requests to standardized JSON/API-ready data for vendors (Stellar Support, Stellar Sales, BlackPoint).
* Establishment of a Single, Auditable Source of Truth: Moving the system of record from disparate email "Sent" folders to a centralized, governed database.

This strategic vision moves the organization toward a model where MSPs eventually receive these payloads via direct API, transforming the service layer into a programmatic extension of our internal logic.

2. The Foundational Rules Engine (The Tripartite Matrix)

The system architecture relies on the logical separation of role definitions, intake logic, and backend execution. This matrix-driven approach is superior to static forms as it allows for role-based entitlements to evolve independently of the user interface.

The Role Matrix (Baseline Entitlements)

This serves as the primary lookup table for default access and hardware provisioning.

Role Profile	M365 Account	Hardware Provisioning	Internal Network / VPN	Comm Systems	Specific Access
Driver	Yes (Basic/F1)	No (Personal Device)	No	Optional Mobile	N/A
Office/Ops	Yes (Standard/E3)	Laptop, Dock, Monitors	Yes (Local/Shares)	Optional Desk/Softphone	Dept DLs, Receptionist System
Manager	Yes (Standard/E3)	Laptop, Dock, Monitors	Yes (VPN Required)	Yes (Direct + Ext)	Elevated Approvals, Management DLs
Warehouse	Yes (Shared/Kiosk)	Shared Workstation	Internal Only	Shared Area Phone	Warehouse Systems
Contractor	Yes (Restricted)	No (BYOD)	VPN (Restricted)	No	Enforced Expiration

The Question Matrix (Dynamic Intake)

To eliminate "form fatigue," the system utilizes conditional branching logic. The UI surfaces only the questions relevant to the selected employment profile:

* Office/Manager Branch: Triggers queries regarding non-standard hardware, specific distribution lists (DLs), shared mailboxes, and receptionist check-in system access.
* Driver Branch: Focuses exclusively on mobile dispatch application requirements.
* Contractor Branch: Mandates a "hard-stop" contract end date for auto-disablement.
* Offboarding Branch: Determines termination priority (Immediate vs. Scheduled) and specifies mailbox conversion or forwarding rules.

The Action Matrix (Automated Execution)

This matrix maps intake data to backend workflows, optimizing vendor interaction through structured delivery.

Intake Condition	Automated Action	Target System / Vendor
New Hire + M365	Generate first.last@freightservices.net account request	Stellar Support
New Hire + Hardware	Generate ticket with shipping details and model specs	Stellar Sales
Phone/Extension Req	Map user to extension/DID via telecom ticket	BlackPoint
Immediate Offboard	Priority access revocation (AD, M365 Sessions, VPN)	Stellar Support
Office/Manager Hire	Trigger API webhook for Receptionist system entry	Google Sheet API

3. Technical Application Architecture & Governance

All internal systems must adhere to the FSI Application Architecture Standard. Standardizing on a Python/Flask stack mitigates technical debt and ensures engineering mobility across the FSI ecosystem.

Core Stack Requirements

* Language: Python 3.10+ (Mandatory).
* Framework: Flask (Modular Blueprints).
* ORM: SQLAlchemy with PostgreSQL.
* Production Server: Gunicorn (WSGI).

Standard Directory Structure

The repository layout is strictly mandated to isolate business logic from orchestration:

/app
  /services      # Business logic (email.py, workflow.py)
  /templates     # Organized by module
    /auth        # RBAC and login templates
    /help        # Documentation and guides
  auth.py        # RBAC and authentication
  models.py      # SQLAlchemy data models
  config.py      # Environment configuration
/migrations      # Alembic migration scripts
wsgi.py          # Production entrypoint


The /services layer is a non-negotiable requirement; business logic must never reside directly in route handlers to ensure testability and clarity.

Architectural Pillars

1. Clarity: Enforced by the Model Constant Rule. All table names must be registered as module-level constants (e.g., USERS_TABLE = "users"). This is essential to prevent corruption during percent-encoding of database URLs (ensuring characters like @ or ? in connection strings do not break the app) and provides a single source of truth for schema metadata.
2. Consistency (UI/UX): FSI applications must utilize the performance-optimized font strategy: Roboto for body copy and Bebas Neue for headings. Templates must include preconnect hints for fonts.googleapis.com and fonts.gstatic.com in the base.html header.
3. Secure-by-Default: Decoupling of secrets from source control is mandatory. The application must implement a Fail-Fast mechanism: if critical secrets are missing in production, the app must refuse to start.

4. Integration & Automation Ecosystem

Postmark Transactional Email

FSI operates under a Postmark-Only Mandate. SMTP is prohibited for new development to ensure deliverability and auditability.

* Template Model Rule: Email bodies must never be hardcoded in Python. Developers must use the template_model (dictionary) to pass dynamic data to templates managed in the Postmark UI.
* Required Variables: POSTMARK_SERVER_TOKEN, MAIL_DEFAULT_SENDER, and a unique MAIL_MESSAGE_STREAM (e.g., onboarding).

Microsoft 365 and SSO

Internal authentication is governed by Microsoft SSO. Staff must access the engine using @freightservices.net credentials. The system acts as the source of truth for user synchronization, pushing requested changes to the Microsoft environment via the Action Matrix.

Database Lifecycle Management

The Alembic Migration Mandate is a non-negotiable governance requirement. Direct SQL execution is deprecated and strictly forbidden to prevent environment drift.

* Health Verification: The application must implement a /readyz endpoint. If schema elements are missing, it must return a 503 status and a response listing the specific missing columns or tables to guide operational recovery.

5. Deployment and Operations (GCP/Cloud Run)

FSI utilizes a serverless containerized model on Google Cloud Run for horizontal scaling and cost-efficiency.

Containerization Strategy

Applications must use a Python-based slim image. The production entrypoint is: gunicorn --bind 0.0.0.0:${PORT} wsgi:app Governance Note: Use of the --factory flag is explicitly forbidden. The application factory is invoked via the wsgi:app syntax, and Gunicorn does not recognize the flag in this configuration.

CI/CD Pipeline (Cloud Build)

The cloudbuild.yaml pipeline executes three stages:

1. Build/Push: Containerize to Artifact Registry.
2. Migration Execution: A standalone blocking job (flask db upgrade) that must succeed before deployment.
3. Service Deployment: Deploy to Cloud Run with automated secret mounting.

Secrets & Security

Required environment variables in Google Secret Manager:

* APP_ENV: (e.g., production or staging)
* FSI_PRODUCTION: The mandatory safety switch for strict validation.
* DATABASE_URL & SECRET_KEY.
* POSTMARK_SERVER_TOKEN & MAIL_MESSAGE_STREAM.

6. Migration Roadmap and Implementation Phases

A phased rollout ensures stability and adoption while transitioning from manual requests to full automation.

Phase	Focus	Deliverables
1: Foundation	Central Intake	Role matrix establishment, core intake form, and auto-generated email drafts for manual review.
2: Automation	Task Orchestration	Automatic task generation, status dashboard, and full Postmark API integration.
3: Optimization	Full Integration	Guided wizard UI, Microsoft SSO/User Sync, and direct API hooks to MSP PSA tools.

Through this implementation, FSI transforms a scattered manual process into a single, auditable source of truth for the FSI digital ecosystem, ensuring the integrity of every identity and asset throughout the employee lifecycle.
