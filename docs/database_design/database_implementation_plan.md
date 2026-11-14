# Database Implementation Plan

**Status:** PHASE_2_DESIGN_DRAFT — implementation sequence for Phase 3. No Django project, model, migration, or database has been created or changed by this plan.

This plan turns the approved schema into Django migrations after Phase 2 review. The current repository does not choose exact PostgreSQL or Django versions, storage provider, or production deployment; those remain gates rather than assumptions.

## Preconditions Before the First Migration

1. Review the [ERD](erd.md), [data dictionary](data_dictionary.md), [constraints and indexes](constraints_and_indexes.md), [lifecycle](data_lifecycle_and_retention.md), and [transaction design](transaction_and_integrity_design.md). Resolve business authority and policy items listed under [remaining decisions](#remaining-decisions).
2. Select supported Django and PostgreSQL versions and record the compatibility/deployment target. Confirm Django support for partial/conditional unique indexes and all chosen check constraints.
3. Add the custom user model in the first migration of its Django app (`0001_initial`), explicitly declare its UUID primary key, set `AUTH_USER_MODEL`, define UUID defaults for every domain model, set `DEFAULT_AUTO_FIELD=BigAutoField` for framework-owned integer-key tables, and set `USE_TZ=True` before generating or applying migrations. Changing `AUTH_USER_MODEL` after initial tables exist is a costly schema/data migration.
4. Confirm final Django app labels and `db_table` names. Every model FK to a human uses `settings.AUTH_USER_MODEL`; role and permission tables are Django auth-owned, not custom clones.
5. Confirm the permission map and the source/evidence policies. Keep database credentials in environment/secret management; this plan defines no credentials.
6. Approve retention periods and legal-hold/erasure behavior before loading non-synthetic data or enabling purge. Keep external response and notification integrations simulated.

## Proposed Migration Sequence

Each stage is a reviewable migration boundary. Update the data dictionary and constraints whenever the implementation departs from this design; do not silently improvise schema changes.

| Stage | Django apps and tables | Dependencies and review points |
|---|---|---|
| 0. Version/configuration gate | No schema | Pin supported versions; configure custom account model, auth settings, UTC timestamps, and database environment before any migration. |
| 1. Identity and audit foundation | Custom User; Django auth Group/Permission joins; AuditEvent | User model is created in its app's first migration. Configure UUID user key. Seed `ADMIN`, `POLICE`, `HOSPITAL` groups through a controlled, idempotent data migration; no AI_SERVICE user or sample credentials. Restrict ordinary app DB role from audit UPDATE/DELETE. |
| 2. Organizations and source registry | Organization, OrganizationMembership, VideoSource | Depend on User and auth Group. Add organization-kind/active checks, membership uniqueness, source authorization/health checks, and approved non-secret source references. Do not store camera credentials. |
| 3. Detection and candidate review | DetectionEvent, Candidate, CandidateDetectionEvent, CandidateReview | Depend on source registry, User, and AuditEvent. Add external event identity, event association uniqueness, status/rationale checks, and candidate review command key. Candidate matching policy must be explicit. |
| 4. Authoritative incidents and histories | AccidentIncident, IncidentStatusHistory, LocationRecord, LocationCorrectionHistory | Depend on Candidate, VideoSource, DetectionEvent, and User. Add unique incident-to-candidate relation and separate incident lifecycle. Preserve camera and accident-location claim distinctions. |
| 5. Evidence metadata and transfer | EvidenceAsset, EvidenceAssociation, EvidenceUploadSession | Depend on VideoSource, DetectionEvent, Candidate, Incident, and User. Add target XOR and partial unique association indexes. Validate migrations against the object-storage abstraction without storing provider credentials or URLs. |
| 6. Independent response workflows | ResponseAssignment, Response, AssignmentStatusHistory | Depend on Incident, Organization, and User. Add target/org checks in domain services, command IDs, terminal/active indexes, and independent histories. |
| 7. Notifications and final index review | Notification, NotificationDeliveryAttempt; remaining query indexes/checks | Depend on Incident/Assignment/User. Keep delivery simulation separate from acknowledgement. Verify indexes against the approved query list; do not add speculative spatial/JSONB indexes. |

The exact split between app migrations may change if Django reports a dependency cycle, especially around the custom user model. Keep the user table in its first app migration and move dependent domain models into later migrations to break cycles; do not change the selected user model after initial migration.

## Migration Review Procedure for Phase 3

1. Generate migrations from reviewed model definitions and inspect every generated operation and dependency.
2. Compare model state against the field dictionary: PostgreSQL type, length/precision, nullability, default, FK target/`on_delete`, and table/column name.
3. Review generated SQL (`sqlmigrate`) for each migration. Confirm CHECK semantics, conditional unique predicates, and absence of duplicate FK indexes. Use explicit named constraints.
4. Apply forward and reverse migration checks against disposable local databases before any approved retained-data environment. Verify seed-role behavior is idempotent and does not remove in-use roles on rollback.
5. Add schema tests and transaction/concurrency/failure tests in Phase 3. Validate migrations from an empty database, inspect migration plan, and verify the API cannot bypass domain authorization.
6. For a data-bearing deployment, take and verify a backup, document downtime/lock impact, deploy additive changes first, backfill in bounded work, and remove old structures only in a later reviewed migration. Do not reverse destructive data migrations as routine rollback.
7. Recheck query plans with representative approved data before adding optional indexes. Consider `CREATE INDEX CONCURRENTLY`, partitioning, PostGIS, or an outbox only after workload and provider decisions justify them.

No step in this document has run. Phase 2 stops before project initialization, `makemigrations`, `migrate`, PostgreSQL table creation, or credential configuration.

## Remaining Decisions

- Supported Django/PostgreSQL versions and deployment target.
- Final candidate grouping and authorized reviewer/verification criteria.
- Organization/source registration and source-owner approval process.
- Object-storage provider, upload-size/type policy, validation/scanning requirement, and object lifecycle.
- Retention periods, legal holds, evaluation data use, account erasure, and backup expiry.
- Assignment eligibility, creation/reassignment authority, resolution/closure authority, and timeout policy; `EXPIRED` remains inactive until approved.
- Location source/precision and correction authority; PostGIS is not needed for MVP numeric coordinate storage and range checks.
- Whether refresh-token revocation, source authorization history beyond AuditEvent, or a transactional notification outbox becomes a real requirement.

