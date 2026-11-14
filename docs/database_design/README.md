# PostgreSQL Database Design

**Status:** PHASE_2_DESIGN_DRAFT — implementation-ready proposal for team review. It does not create or claim database tables, Django models, or migrations.

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

All details are proposed design, not deployed behavior. Retention durations, legal-hold handling, exact PostgreSQL/Django versions, object-storage provider, reviewer authority, assignment authority, and timeout policy remain subject to the approvals listed in the documents. Phase 2 introduces documentation only: no Django initialization, model code, migrations, credentials, or database objects are part of this design.
