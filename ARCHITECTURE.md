Briefing Document: Onboarding and Offboarding Rules Engine Architecture

Executive Summary

The following document outlines the foundational architecture and technical implementation plan for a standardized employee lifecycle management system. The core objective is to transition from a decentralized, manual process of communicating with Managed Service Providers (MSPs)—specifically Stellar Support, Stellar Sales, and BlackPoint—to a unified, automated rules engine.

This system utilizes a tripartite matrix structure—Role, Question, and Action—to govern entitlements and automate workflows. Implementation will leverage a Flask-based Python architecture, integrated with a PostgreSQL database and Postmark for transactional email delivery. The application is designed for containerized deployment on Google Cloud Run, ensuring scalability and consistency across the Freight Services Inc. (FSI) digital ecosystem.


--------------------------------------------------------------------------------


I. Foundational Rules Engine Architecture

The system operates on three distinct matrices that separate role definitions from intake logic and automated execution.

1. The Role Matrix (Baseline Entitlements)

This serves as the primary lookup table, defining default access and hardware provisioning based on the employment profile.

Role Profile	M365 Account	Hardware Provisioning	Internal Network / VPN	Comm Systems	Specific Access
Driver	Yes (Basic/F1)	No (Personal Device)	No	Optional Mobile	N/A
Office/Ops	Yes (Standard/E3)	Laptop, Dock, Monitors	Yes (Local/Shares)	Optional Desk/Softphone	Dept DLs, Receptionist
Manager	Yes (Standard/E3)	Laptop, Dock, Monitors	Yes (VPN Required)	Yes (Direct + Ext)	Elevated Approvals
Warehouse	Yes (Shared/Kiosk)	Shared Workstation	Internal Only	Shared Area Phone	Warehouse Systems
Contractor	Yes (Restricted)	No (BYOD)	Restricted VPN	No	Enforced Expiration

2. The Question Matrix (Dynamic Intake Logic)

To prevent "form fatigue," the front-end UI utilizes conditional branching. Questions are triggered only when relevant to the selected Role Profile.

* Global Fields: Legal Name, Preferred Name, Start Date, Manager, Location, and Role Profile.
* Office/Manager Branch: Triggers questions regarding non-standard hardware, specific distribution lists (DLs), shared mailboxes, and dedicated external phone numbers.
* Driver Branch: Focuses on mobile dispatch application access.
* Contractor Branch: Requires a mandatory "hard-stop" contract end date for auto-disablement.
* Offboarding Branch: Determines if the exit is immediate (high priority SLA) or scheduled, and handles mailbox conversion/forwarding requirements.

3. The Action Matrix (Automated Execution)

This maps intake data to backend workflows, generating specific payloads for target systems.

* Account Creation: If M365 is required, a ticket is routed to Stellar Support in the format first.last@freightservices.net.
* Hardware Procurement: If hardware is selected, a ticket with shipping details and specs is routed to Stellar Sales.
* Telecom Provisioning: If a phone/extension is needed, a ticket is routed to BlackPoint mapping the user to an extension/DID.
* Immediate Offboarding: Triggers critical access revocation (Disable AD, Revoke M365 Sessions, Kill VPN) via high-priority email to Stellar Support.


--------------------------------------------------------------------------------


II. Technical Application Architecture

The application follows the FSI Application Architecture Standard, a proven stack utilized across various internal repositories such as EXPENSES, FSI_POD, and QUOTES.

1. Core Stack Requirements

* Language: Python 3.8+ (3.10+ recommended).
* Framework: Flask (utilizing Blueprints for modularity).
* Database: PostgreSQL (production) or local PostgreSQL for development.
* ORM: SQLAlchemy for data modeling.
* Migrations: Alembic (via Flask-Migrate) for schema management.
* Production Server: Gunicorn (WSGI).

2. Standard Directory Structure

The application should adhere to the established layout found in the fsi_STRUCTURE_EXAMPLE repository:

* app/auth.py: Handles authentication, registration, and RBAC (Role-Based Access Control).
* app/models.py: Contains SQLAlchemy models and centralized table name constants (e.g., USERS_TABLE).
* app/services/: Contains logic for the rules engine and external integrations (email, workflow).
* app/config.py: Manages environment variables and runtime settings.
* templates/: Jinja2 templates for the UI, following FSI design principles (Bebas Neue for headings, Roboto for body).


--------------------------------------------------------------------------------


III. Integration and Automation Strategy

1. Postmark Transactional Email Integration

Postmark is the mandatory provider for all outbound communications to MSPs. This ensures high deliverability for critical tickets.

* Implementation: Create an app/services/email.py layer to abstract API calls.
* Template Model: Instead of hardcoding email bodies in Python, use Postmark's web UI to build templates (e.g., offboarding-immediate, new-user-account).
* Payload Delivery: The Flask app pushes dynamic data (e.g., {{employee_name}}, {{start_date}}) to the Postmark API.
* Configuration: Requires POSTMARK_SERVER_TOKEN and MAIL_DEFAULT_SENDER.

2. Microsoft 365 and SSO

The architecture prioritizes alignment with the existing Microsoft 365 environment.

* User Sync: The system should look into Microsoft SSO for user authentication and synchronization, ensuring that internal staff can access the tool using their standard @freightservices.net credentials.
* Identity Management: The system acts as the source of truth for requested changes, which are then pushed to Microsoft 365 via Stellar Support tickets or direct API integrations.

3. Database Schema Policy

* Table Constants: Every new database table must be registered as a module-level constant in models.py (e.g., ROLE_MATRIX_TABLE = 'role_matrix').
* Alembic Migrations: SQL scripts are for historical reference only. All schema rollouts must be executed via flask db upgrade or alembic upgrade head.


--------------------------------------------------------------------------------


IV. Deployment and Operations

1. Containerization (Docker)

The application must be containerized for consistency across environments.

* Base Image: Python-based slim image.
* Entrypoint: gunicorn --bind 0.0.0.0:${PORT} wsgi:app.
* Local Entrypoint: python wsgi.py.

2. Google Cloud Platform (GCP) Integration

* Hosting: Google Cloud Run.
* CI/CD: Google Cloud Build (cloudbuild.yaml) to automate image building and deployment.
* Secrets Management: Critical values (e.g., DATABASE_URL, SECRET_KEY, POSTMARK_SERVER_TOKEN) must be stored in GCP Secret Manager and mounted as environment variables.
* Health Checks: Implementation of /healthz or /readyz endpoints to validate database connectivity and schema readiness before shifting traffic.


--------------------------------------------------------------------------------


V. Implementation Phases

Phase	Focus	Deliverables
Phase 1: Foundation	Central Intake	Role matrix, core intake form, and auto-generated email drafts for manual review.
Phase 2: Automation	Task Orchestration	Automatic task generation, status dashboard, and Postmark API integration.
Phase 3: Optimization	Full Integration	Guided wizard UI, Microsoft SSO/User Sync, and direct API hooks to MSP PSA tools.

This architecture eliminates the "scattered" nature of current MSP requests by consolidating all identity, hardware, and access workflows into a single, auditable source of truth.
