# PostgreSQL Database Design

**Status:** Phase 2B database foundation implemented locally. These documents describe the logical and physical design represented by the Django models and migrations; institutional retention, authorization, and operational policy decisions remain pending.

PostgreSQL is the authoritative store for structured application data. Object storage holds evidence bytes; Django owns persistence and authorization. The AI service submits observations but cannot verify candidates, create incidents, or change response state. Police and Hospital assignments have independent lifecycles.

## Design Documents

- [ERD](erd.md) — entities, relationships, cardinality, and MVP/future evaluation.
- [Data dictionary](data_dictionary.md) — proposed field-level types, nullability, defaults, keys, indexes, validation, and sensitivity.
- [Schema specification](database_schema_specification.md) — ownership, primary-key/auth decisions, table inventory, and conventions.
- [Constraints and indexes](constraints_and_indexes.md) — proposed foreign keys, unique/check constraints, and query indexes.
- [Lifecycle and retention](data_lifecycle_and_retention.md) — soft deletion, media cleanup, audit preservation, and policy-dependent durations.
- [Transaction and integrity design](transaction_and_integrity_design.md) — atomic boundaries, retries, idempotency, concurrency, and storage reconciliation.
- [Implementation plan](database_implementation_plan.md) — decisions and migration sequence for the later Django implementation phase.

## Status and Scope

The Django project and MVP schema migrations exist and have been applied to a dedicated local PostgreSQL 18.7 development database. PostgreSQL objects exist only in that local database; this does not represent a production deployment. Python 3.14.10, Django 5.2.19, Django REST Framework 3.18.3, Psycopg 3.3.9, and PostgreSQL 18.7 are the current development compatibility baseline. Retention durations, legal-hold handling, object-storage provider, reviewer/assignment authority, and timeout policy remain subject to institutional/team approval. APIs, domain transition services, storage operations, and real emergency integrations are out of scope for Phase 2B.
