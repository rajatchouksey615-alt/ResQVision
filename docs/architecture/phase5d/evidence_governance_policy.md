# Evidence Governance Policy

**Decision status:** Proposed principles; access, storage, and retention require approval.  
**Related existing decisions:** OAD-002, OAD-014, OAD-016, OAD-017.  
**Related requirements:** FR-006, FR-025 through FR-027; NFR-006, NFR-007, NFR-008, NFR-010, NFR-022.

## Scope and Classification

EvidenceAsset metadata and media bytes are different protected resources. PostgreSQL stores metadata and an opaque storage reference; object storage holds bytes. Recommend three handling classes, subject to institutional data classification:

| Class | Examples | Baseline handling |
|---|---|---|
| Restricted media | Original/derived video or images, identifiable people/vehicles, audio if ever supported | Private storage; no public access; exact object-level authorization; minimize copies; controlled retention/deletion. |
| Sensitive evidence metadata | Original filename, source/event/time, media type/size, checksum, precise location reference, association, validation/scan status | Backend-only by default; expose only fields needed for the approved role and assignment purpose. Do not expose object keys or storage details to clients. |
| Operational provenance | Asset UUID, lifecycle state, validation outcome, upload/session result, actor/time audit references | Still access-controlled; expose a minimal safe status only when needed. Never expose credentials, signed URLs, raw provider responses, or media bytes in logs. |

This proposal does not establish a legal classification label, admissibility standard, or retention duration.

## Access Policy

| Operation | Recommended principal and scope | Preconditions | Current repository state |
|---|---|---|---|
| View metadata | Explicitly authorized human with a relevant candidate/incident assignment; field-level minimization. Admin requires a separately scoped need. | Active identity/membership, resource association, approved purpose, and policy. | Evidence object permission always denies; list/detail endpoints return 503. |
| Retrieve media | Same approved role/object scope, evaluated separately from metadata. | Asset `AVAILABLE`; current object authorization; integrity/object exists; request is audited. | No usable retrieval endpoint/provider contract; route unavailable. |
| Create/upload media | AI_SERVICE only for its server-issued, single-asset upload authorization; any human upload requires a separately approved workflow. | Configured machine auth; active upload session; private object; bounded expiry/object/type/size; validation before `AVAILABLE`. | Evidence models and lifecycle coordination exist; no provider/verifier is configured, upload API returns 503. |
| Associate evidence | Backend policy or explicitly authorized evidence reviewer; only a validated asset and allowed source/candidate/incident relationship. | Preserve source and original link; require reason/audit for changes. | `EvidenceAssociation` supports one target per association row (source, candidate, or incident); no usable association API policy. |
| AI_SERVICE read | No general browsing or retrieval. | May receive only its own upload completion/result contract if approved. | Current machine contract is unconfigured; no general read permission. |
| Delete/invalidate | Designated data custodian under approved retention/deletion policy; operationally separate approval may be needed. | First revoke access/expire, then idempotent external deletion, then tombstone after absence confirmation. | Lifecycle states are modeled; retention durations, authority, jobs, and provider deletion adapter are not approved/implemented. |

Police and Hospital should not automatically receive the same media or metadata. Their assignment scopes remain independent; access to a shared incident asset must be an explicit policy grant for each target. Admin status alone does not grant broad evidence access.

## Media Retrieval and Transfer

Keep media private. Each operation must be authorized by the backend and scoped to one immutable asset/object. OAD-016 proposes short-lived, single-object transfer authorization where the selected provider supports it, with backend-mediated upload as a fallback. Do not implement or document signed-URL behavior as selected until the provider is approved. Retrieval can be backend-mediated or use a future short-lived read grant only after the provider and privacy review approve the exact flow. No public URL, broad bucket credential, permanent client token, or user-supplied object key is acceptable.

## Integrity, Provenance, and Association

Preserve creator identity (`AI_SERVICE` or human), source DetectionEvent, object identity, media type, positive size, SHA-256 checksum, validation time, upload time, scan status, retention reference, and association history where available. Only `AVAILABLE` is retrievable. The model constraint requires populated size, checksum, media type, validation/upload timestamps, and passed/not-required scan before `AVAILABLE`.

Never overwrite original bytes silently. A corrected/derived artifact should be a new EvidenceAsset with an explicit provenance relationship once that relationship is defined. Candidate verification must not mean an asset is admissible, conclusive, or accessible to every incident participant.

## Lifecycle and Retention

The modeled lifecycle includes `PENDING_UPLOAD`, `UPLOADING`, `QUARANTINED`, `AVAILABLE`, `FAILED`, `EXPIRED`, and `DELETED`. Expiry must disable retrieval before object deletion. External deletion occurs outside the database transaction; retries must target the same immutable object identity and mark metadata deleted only after absence is confirmed. On uncertainty, keep media inaccessible and reconcile.

All retention periods are TBD in `docs/database_design/data_lifecycle_and_retention.md`. Approval is required for raw source video, derived evidence, rejected-candidate media, verified incident evidence, audit and backup retention, legal-hold owner/release, deletion request/approval roles, and evaluation-copy reuse. Do not add an automated purge or claim deletion until an approved policy and provider workflow exist.

## Audit and Logging

Audit metadata listing, authorized media retrieval, denied access, upload authorization/completion/validation/failure, association changes, expiry, deletion request, confirmed deletion, and reconciliation outcome. Capture actor/service, asset UUID, target, outcome, UTC timestamp, request/command ID, and safe failure code. Exclude media, passwords/tokens, signed URLs, credentials, raw storage payloads, and unnecessary personal data. Audit reader scope and retention are separate approvals.

## Decisions Required Before Enablement

Approve storage provider and data location; allowed media types/sizes and scanning requirements; upload and retrieval contract; role-specific metadata fields/media access; whether a candidate and resulting incident share the same asset authorization; evidence association and correction authority; retention periods and legal holds; deletion authority and recovery; and audit visibility. Until these are approved, evidence endpoints remain blocked.
