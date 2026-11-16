# ResQVision Backend

**Status:** The Django configuration, PostgreSQL database foundation, and internal domain service layer are implemented. The backend is not yet an HTTP API or an operational response service.

## Django Project Configuration

- `manage.py` is the command-line entry point and defaults to `config.settings.development`.
- `config/settings/base.py` contains shared Django, auth, UTC, and PostgreSQL settings. `config/settings/development.py` adds local-only development settings; `config/settings/test.py` configures the automated test environment.
- `config/urls.py`, `config/asgi.py`, and `config/wsgi.py` are the project entry points. URL routing currently exposes Django admin only.
- A private repository-root `.env` may supply local settings. It is ignored by Git; do not put shared or production credentials in it.

## Implemented Database Foundation

The ten Django applications each own a persistence domain:

- `accounts`: custom `User` model; Django auth Groups seeded as `ADMIN`, `POLICE`, and `HOSPITAL`.
- `organizations`: `Organization` and `OrganizationMembership`.
- `sources`: `VideoSource` authorization and availability metadata.
- `detection`: source-scoped, provenance-aware `DetectionEvent` records.
- `incidents`: `AccidentCandidate`, `CandidateDetectionEvent`, `CandidateReview`, authoritative `AccidentIncident`, and `IncidentStatusHistory`.
- `evidence`: `EvidenceAsset`, typed `EvidenceAssociation`, and `EvidenceUploadSession` metadata.
- `locations`: provenance-aware `LocationRecord` and `LocationCorrectionHistory`.
- `responses`: independent `ResponseAssignment` records, append-only `Response` activities, and `AssignmentStatusHistory`.
- `notifications`: `Notification` records and separate simulated `NotificationDeliveryAttempt` history.
- `audit`: append-only `AuditEvent` records.

The custom `accounts.User` uses a UUID primary key, normalized unique email as its login identifier, and Django's password hashing. ResQVision-owned domain records use UUID keys. Django's built-in Group and Permission tables keep their migration-defined integer keys.

Each application has tracked migrations under `apps/<app>/migrations/`. They define the database tables, foreign keys, checks, unique constraints, and query indexes. Apply them to the configured local database with `manage.py migrate`. The [database design documents](../docs/database_design/README.md) contain the ERD, field dictionary, constraints, lifecycle decisions, and transaction boundaries.

## Internal Domain Services

Services live under each owning app's `services/` package and accept typed actor and command inputs. They enforce state transitions, transaction boundaries, idempotency, and audit behavior without depending on HTTP request objects:

- `common/domain/`: human and machine actor contexts, domain exceptions, typed command results, and deny-by-default policy interfaces.
- `audit/services/`: allow-listed audit events with safe context and actor snapshots.
- `detection/services/`: provenance validation, authorized-source event ingestion, semantic replay handling, and object-scoped reads.
- `incidents/services/`: candidate/event association, review workflow, atomic verified incident creation, and incident lifecycle transitions.
- `organizations/services/` and `sources/services/`: membership lifecycle and video-source registration/authorization operations.
- `responses/services/`: independent agency assignments, acknowledgement, response activity, cancellation, reassignment, resolution, and closure policy hooks.
- `evidence/services/`: upload-session and evidence metadata lifecycle, access checks, and staged deletion without a storage provider.
- `locations/services/`: provenance-aware location claims, verification, correction history, and current-claim reads.
- `notifications/services/`: simulated notification creation, delivery attempts, recipient reads, and cancellation.

Unresolved authority decisions fail closed through `PolicyNotConfigured`; tests inject narrowly scoped policies. This includes candidate verify/reject, source register/authorize, assignment, incident resolve/close, and administrator override authority. No role is silently granted these powers.

## Dependencies

The supported local Python version is recorded in `.python-version` (`3.14.10`). Runtime dependencies are pinned in `requirements/base.txt` and include Django, Django REST Framework, Psycopg, and `python-dotenv`. `requirements/development.txt` adds pytest, pytest-django, and Ruff. `requirements/production.txt` contains runtime pins; it does not configure or imply a production deployment.

## Local PostgreSQL Setup

Create a private repository-root `.env` from `.env.example` and set local-only values. The settings read `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`; defaults target `resqvision_dev` on `127.0.0.1:5433`.

The optional PostgreSQL 18.7 Compose service binds only to loopback. From the repository root, start it with:

```powershell
docker compose --env-file .env -f infrastructure/docker/compose.database.yml up -d postgres
```

A dedicated local PostgreSQL cluster can be used instead if Docker Engine is unavailable; configure it to match the `.env` connection settings. Keep development and test databases isolated from shared or production databases. The test database role needs permission to create the separate database used by pytest.

## Validation and Database Tests

From `backend/`, create an isolated environment and install development dependencies:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements\development.txt
```

With the local PostgreSQL database available, run schema and test checks from `backend/`:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pip check
```

`pytest.ini` selects `config.settings.test`. Tests use PostgreSQL and a separate test database; the current suite passes 67 tests, including service integration, rollback, idempotency, and concurrency coverage. The test-only password hasher and secret are not deployment settings.

## Implementation Boundaries

Django admin is available. REST endpoints, JWT/login/token workflows, mobile authentication, and client-facing serializers are not implemented. Domain services provide internal business operations, but authority remains policy-injected where project decisions are open. AI processing, mobile integrations, actual object-storage operations, external notification delivery, and production deployment are also unimplemented. Notifications and Police/Hospital response records remain simulated; no real emergency integration is configured.
