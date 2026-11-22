# Database Foundation Implementation Record

**Status:** The database schema and internal domain services are implemented and validated against a dedicated local PostgreSQL development database. This is not a production deployment and does not include HTTP APIs or external integrations.

## Selected Development Baseline

| Component | Version/configuration |
|---|---|
| Python | `3.14.10`, recorded in `backend/.python-version` |
| Django | `5.2.19` |
| Django REST Framework | `3.18.3` |
| Psycopg | `3.3.9` binary development extra |
| PostgreSQL | `18.7`, local-only cluster on port `5433`; Compose definition uses `postgres:18.7` |
| Primary keys | UUIDv4 for ResQVision-owned rows; Django auth Group/Permission use migration-defined `integer` keys |
| Time | `USE_TZ=True`, UTC |

Dependencies are pinned in `backend/requirements/`. Django's custom user model was selected before any migration and uses UUID identity with normalized unique email; Django remains responsible for password hashing and auth relations. Django Groups seed `ADMIN`, `POLICE`, and `HOSPITAL`; `AI_SERVICE` is not a human user or Group.

## Implemented MVP Schema

The Django apps and migrations persist accounts, organizations/memberships, video sources, detection events, candidates and review, authoritative incidents and history, evidence metadata/associations/upload sessions, location claims/corrections, independent response assignments/activities/history, notifications/delivery attempts, and audit events. Full field definitions, relationships, indexes, deletion rules, and retention decisions are in the [data dictionary](data_dictionary.md), [ERD](erd.md), [schema specification](database_schema_specification.md), [constraints and indexes](constraints_and_indexes.md), [lifecycle design](data_lifecycle_and_retention.md), and [transaction design](transaction_and_integrity_design.md).

Applied migration sequence:

| App | Migrations |
|---|---|
| `accounts` | `0001_initial`, `0002_seed_role_groups` |
| `audit`, `organizations`, `sources`, `detection`, `incidents` | `0001_initial` |
| `evidence` | `0001_initial`, `0002` check-constraint correction, `0003` remove redundant FK indexes and preserve named conditional uniqueness |
| `locations` | `0001_initial`, `0002` creator-check correction, `0003` remove redundant provenance FK indexes and index location subjects/history |
| `responses` | `0001_initial`, `0002` check-constraint correction, `0003` named replacement uniqueness |
| `notifications` | `0001_initial`, `0002_initial` dependency split, `0003` check-constraint correction, `0004` remove redundant FK indexes, `0005` delivery-attempt command idempotency |

Migration SQL was inspected with `sqlmigrate` before application. Named checks and partial unique indexes protect row-local vocabularies, identities, current claims, active assignments/uploads, evidence availability, delivery-attempt command IDs, and audit/response histories. Cross-row authorization and state transitions are implemented in domain services and transactions, with unresolved authorities failing closed.

## Local Development and Verification

- PostgreSQL database `resqvision_dev` and role `resqvision_app` are isolated on loopback port `5433`; local credentials live only in the ignored root `.env` and local cluster files.
- `infrastructure/docker/compose.database.yml` defines the optional local PostgreSQL container. Docker Engine was unavailable during this implementation, so the Compose service was not started; the isolated local PostgreSQL 18.7 cluster was used instead.
- The PostgreSQL-backed test suite creates a separate test database and currently passes **87 tests**: 67 persistence/domain tests and 20 API security/integration cases. Coverage includes model constraints, service behavior, rollback, idempotency, authorization, API token lifecycle, scoped throttling, machine-auth boundaries, and a real PostgreSQL candidate-verification race.
- `manage.py check` reported no issues; `makemigrations --check --dry-run` found no model drift; `pip check`, Ruff lint/format, and `git diff --check` passed. The Compose file was parsed but not started because Docker Engine was unavailable.

Use a private local `.env`, never production/shared credentials. Do not add actual video, image, camera, storage, emergency-response, or user secrets to Git.

## Deliberate Boundaries and Remaining Decisions

- No Django API endpoints, JWT flow, AI service, Flutter work, object-storage adapter, production database credentials, or emergency-service integration is implemented.
- Evidence rows store private object metadata and opaque storage references only. Object storage/provider choice and deletion reconciliation remain pending.
- Candidate verification/rejection, source registration/authorization, assignment creation, incident resolution/closure, and administrator override authority remain TBD until team/institutional approval; affected operations use explicit deny-by-default policy hooks. Retention periods, legal holds, scan requirements, account erasure, and assignment timeout policy also remain TBD. No authority or duration has been invented.
- Candidate verification/incident creation, incident and assignment transitions, response activity, evidence metadata lifecycle, location claims, and simulated notifications are executable internal services; object-storage actions remain adapter work.
- The design does not add PostGIS, triggers, custom SQL types, or speculative indexes.

## Next Development Step

Next, obtain team decisions for the unresolved authority hooks and document approved policies. Then define and review the internal-to-HTTP boundary before implementing APIs. Object-storage reconciliation, client integrations, and deployment remain later work. Keep the configured `accounts.User` model unchanged; replacing it after initial migrations would require a high-risk schema/data migration.
