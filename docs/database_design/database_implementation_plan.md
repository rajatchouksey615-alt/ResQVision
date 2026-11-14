# Database Foundation Implementation Record

**Status:** Phase 2B database foundation implemented and validated against a dedicated local PostgreSQL development database. This is not a production deployment and does not include API/domain services.

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
| `notifications` | `0001_initial`, `0002_initial` dependency split, `0003` check-constraint correction, `0004` remove redundant FK indexes |

Migration SQL was inspected with `sqlmigrate` before application. Named checks and partial unique indexes protect row-local vocabularies, identities, current claims, active assignments/uploads, evidence availability, and audit/response histories. Cross-row authorization and state transitions remain the responsibility of Phase 3 domain services and transactions.

## Local Development and Verification

- PostgreSQL database `resqvision_dev` and role `resqvision_app` are isolated on loopback port `5433`; local credentials live only in the ignored root `.env` and local cluster files.
- `infrastructure/docker/compose.database.yml` defines the optional local PostgreSQL container. Docker Engine was unavailable during this implementation, so the Compose service was not started; the isolated local PostgreSQL 18.7 cluster was used instead.
- The PostgreSQL-backed test suite creates a separate test database and currently passes **50 tests** covering model constraints and persistence behavior.
- `manage.py check` reported no issues; `makemigrations --check --dry-run` found no model drift; `pip check`, Ruff lint/format, Compose configuration parsing, local Markdown-link validation, and `git diff --check` passed. The Compose file was parsed but not started because Docker Engine was unavailable.

Use a private local `.env`, never production/shared credentials. Do not add actual video, image, camera, storage, emergency-response, or user secrets to Git.

## Deliberate Boundaries and Remaining Decisions

- No Django API endpoints, JWT flow, AI service, Flutter work, object-storage adapter, production database credentials, or emergency-service integration is implemented.
- Evidence rows store private object metadata and opaque storage references only. Object storage/provider choice and deletion reconciliation remain pending.
- Retention periods, legal holds, reviewer/assignment authority, source authorization procedure, scan requirements, account erasure, and assignment timeout policy remain TBD until team/institutional approval. No duration has been invented.
- Incident/assignment transition graphs and candidate verification/incident creation are described transactionally but are not executable domain services yet.
- The design does not add PostGIS, triggers, custom SQL types, or speculative indexes.

## Next Development Step

Phase 3 should implement the reviewed Django domain services and authorization before API endpoints: candidate decision and incident creation atomically, state-transition services with row locking and command idempotency, organization-scoped assignments, and evidence object-storage reconciliation. Keep the configured `accounts.User` model unchanged; replacing it after initial migrations would require a high-risk schema/data migration.
