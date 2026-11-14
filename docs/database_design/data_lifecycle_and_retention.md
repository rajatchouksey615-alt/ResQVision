# Data Lifecycle and Retention

**Status:** PHASE_2_DESIGN_DRAFT — lifecycle controls are proposed; retention durations and legal-hold rules require institutional approval. No retention job or deletion operation is implemented.

This document defines how records become inactive, remain attributable, and are eventually removed. Do not enable production-like ingestion or automated purge until the institution approves purpose, retention periods, authorized deletion roles, and legal-hold handling. Every duration below is deliberately **TBD**.

## Record Retention Matrix

| Record/data | Ordinary lifecycle | Retention duration | Deletion or preservation rule |
|---|---|---|---|
| Human account and role grants | `is_active=false`; revoke memberships and role grants during offboarding | TBD | No cascade deletion. An approved erasure may anonymize identity fields; retained relationships and audit references require a documented institutional decision. |
| Organization and membership | Organization deactivation; membership `SUSPENDED` or `REVOKED` | TBD | Preserve membership and assignment history. Do not delete an organization that is referenced by retained records. |
| VideoSource authorization/configuration | `SUSPENDED` or `REVOKED`; health is separate | TBD | Revocation blocks new processing immediately. Keep a non-secret source record and authorization audit while retained events depend on its provenance. Remove configuration references when no longer needed. |
| DetectionEvent and candidate | Immutable event provenance; candidate ends `VERIFIED` or `REJECTED` | TBD | Preserve rejected candidates and their review rationale/history for the approved evaluation/audit period. Do not convert model confidence into a deletion or verification rule. |
| AccidentIncident, assignments, responses, and histories | Incident `RESOLVED`/`CLOSED`; assignment terminal state | TBD | Preserve business histories and provenance. No cascade deletion from incident or organization. Any erasure exception must be reviewed against the retention/hold policy. |
| Evidence media bytes | Private object; accessible only while asset is `AVAILABLE` and authorized | TBD per policy reference | Revoke access first, delete object asynchronously, retry idempotently, then mark metadata `DELETED`. Keep a tombstone and authorized deletion audit unless approved erasure requires more. |
| Evidence metadata and upload sessions | Asset state and upload-session outcomes | TBD | Retain opaque object identity, validation/deletion outcomes, checksums, and safe failure codes only as long as needed. Never retain signed URLs or storage credentials. |
| Location claims and corrections | Current claim plus superseded rows and append-only corrections | TBD | Treat coordinates and accuracy as sensitive. Preserve correction provenance as required; purge or coarsen coordinates only under an approved rule that also handles history and backups. |
| Notifications and delivery attempts | Simulation state; attempts are separate rows | TBD | Notification cleanup must not change an assignment or incident. Do not introduce live provider delivery through retention work. |
| AuditEvent | Append-only for ordinary application role | TBD | No application update/delete. Restrict access and redact inputs before storage. Database owner access and backup lifecycle remain operational controls, not tamper-proof guarantees. |
| Backups and replicas | Operational copies | TBD | Backup expiry must be coordinated with approved deletion/hold policy. A restore may reintroduce a pre-deletion metadata state and therefore requires reconciliation before evidence access. |

`retention_policy_ref` stores a stable policy code, not a duration or secret. A policy catalog or legal-hold entity is not added in MVP because no owner, schema, or approval process is defined. If the system must enforce individual holds, add an explicit reviewed model before enabling purge; until then, purge automation stays disabled where a hold may apply.

## Deactivation, Soft Deletion, and Hard Deletion

- **User offboarding:** Set `is_active=false`, revoke applicable memberships, remove role grants, and invalidate authentication through the approved session/token mechanism. This prevents new access while keeping actor and ownership links intact. Do not use `is_superuser` as an ordinary application role.
- **Anonymization/erasure:** Exact identity-field replacement and any hard-delete exception require institutional privacy review. AuditEvent can retain an opaque `actor_ref_snapshot` if its `actor_user_id` FK is nulled under approved erasure. Other retained foreign keys use `PROTECT`; do not silently break those links or erase required history. A future token/session table is not part of this schema.
- **Business records:** Candidate, incident, assignment, response, review, location correction, and audit records have no generic `is_deleted` flag. Use their explicit terminal/revoked state and retain histories. Hard deletion requires an approved retention operation with dependency review.
- **Evidence:** `EXPIRED` means access is disabled and media deletion is due or in progress; `DELETED` is set only after the object is confirmed absent. Metadata remains as a tombstone for the approved duration. New uploads use a fresh `EvidenceUploadSession`; never reuse a permanent signed URL.
- **Source video:** A controlled-file VideoSource points to a private source-video EvidenceAsset through EvidenceAssociation. Revoking a source blocks new ingestion; deleting its source file follows the same evidence deletion workflow and does not silently erase accepted event provenance.
- **Audit and histories:** Append-only rows are not cascade-deleted when users, sources, candidates, incidents, or assignments are disabled. Operational database roles should not have `UPDATE`/`DELETE` permission on AuditEvent. Retention purge is an explicitly privileged, reviewed operation.

## Evidence Deletion and Storage Reconciliation

PostgreSQL and object storage do not share a transaction. Use the EvidenceAsset row as a durable deletion work item rather than assuming a distributed transaction:

1. In one PostgreSQL transaction, lock the asset, verify the authorized actor and applicable retention/hold decision, transition it to `EXPIRED`, set `expired_at`, and append an audit event. Retrieval authorization immediately denies `EXPIRED` assets.
2. After commit, a worker requests deletion using the opaque provider/namespace/object key. The operation is idempotent: a confirmed “not found” is treated as deleted. Record safe attempt/failure codes in AuditEvent; never record credentials, signed URLs, or raw provider payloads.
3. On confirmed absence, a second transaction locks the asset, sets `DELETED` and `deleted_at`, and appends the completion audit event. On transient failure, keep it `EXPIRED` with `deleted_at=NULL`; the worker retries and operators can reconcile it.
4. If the object was never created, the worker confirms absence and closes the metadata lifecycle the same way. Do not claim deletion before checking the external object state.
5. Before returning bytes for an `AVAILABLE` asset, the backend still applies current authorization and checks the object retrieval result. A missing object is not served; record a safe failure and reconcile the asset state.

After a database restore, reconcile `AVAILABLE`, `EXPIRED`, and `DELETED` metadata against object storage before enabling retrieval or purge. Keep retention processing idempotent so repeated work cannot recreate access or delete a different object. Object keys are server-generated and unique per provider/namespace.

## Policy Decisions Required

- Approved duration and trigger for raw source video, derived evidence, rejected candidates, incidents, assignment/notification history, AuditEvent, and backups.
- Whether evaluation copies may outlive operational evidence and, if so, how consent, de-identification, and dataset provenance are represented.
- Who may request/approve evidence deletion and what separation of duties is required.
- Legal-hold owner, applicability, release, and whether holds must be represented as first-class records.
- Whether location precision may be reduced or removed while preserving correction/audit history.
- Account erasure/anonymization semantics where retained foreign keys and research records remain.

