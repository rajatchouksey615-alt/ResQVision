# Domain Governance and Architecture Decision Resolution

Domain Governance and Policy Review

**Status: PARTIALLY_RESOLVED**  
**Approval package:** Ready for project-team and domain-stakeholder review  
**Scope:** Repository audit and documentation only. No code, permission, schema, migration, or runtime-policy changes were made.

## Executive Summary

ResQVision already has a useful separation between AI observations, candidates, verified incidents, agency assignments, evidence metadata, and location claims. Django services and database constraints implement several integrity controls, including transactional candidate verification, independent agency assignment records, scoped incident reads, append-oriented audit records, and fail-closed policy hooks.

The governance baseline is not fully approved. The SRS, requirements, workflows, role-permission matrix, architecture, and OAD register remain `REVISED_DRAFT` or proposed, and existing code is not evidence of approval. A project-owner task dated 2026-11-19 now explicitly approves the conceptual Police-first verification and simulated Hospital response sequence. That approval fixes role order and workflow outcomes only; it does not grant runtime permissions or settle reviewer identity/scope, Hospital routing, response-state contracts, evidence/location access, or retention. The scoped approval and remaining gates are recorded in the [Accident Verification and Emergency Response Governance Workflow](accident_verification_emergency_response_workflow.md).

Keep privileged operations unavailable until the remaining action authority, identity, scope, and contracts are recorded. Preserve fail-closed behavior while those details are pending. The owner-approved sequence is a governance decision, not authorization to enable the routes.

## Repository Audit

The audit inspected the requirements set (SRS, FRs, NFRs, use cases, role-permission matrix, and RTM), architecture and data-flow documents, conceptual ERD and data dictionary, schema constraints, transaction and retention designs, workflow documents, OAD-001 through OAD-021, the historical [incident management engineering report](../../incident_management/incident_management_report.md), API authorization documentation, and the related Django models, services, policies, selectors, serializers, routes, audit services, and tests.

Relevant implementation areas include `backend/apps/incidents`, `backend/apps/detection`, `backend/apps/evidence`, `backend/apps/locations`, `backend/apps/responses`, `backend/apps/organizations`, `backend/apps/audit`, and `backend/api/v1`. The repository contains an incident/candidate workflow, but does not contain separate approved evidence-access or location-provenance workflow documents. Retention durations and legal-hold rules remain TBD.

Relevant tests inspected include `backend/tests/test_domain_services.py` (candidate verification atomicity/idempotency and concurrency, resolution/closure policy, independent assignments, evidence validation/expiry, location correction and camera separation), domain model tests under `backend/apps/*/tests/`, and `backend/api/tests/test_api.py` (assignment scope, safe 404 concealment, policy-blocked 503 behavior, and machine-auth fail-closed behavior). These test files were reviewed as implementation evidence but were not executed for this documentation task.

The architecture README and system/component architecture headers previously stated that no services or APIs were implemented. That statement conflicted with the current Django domain services, selected REST endpoints, and Flutter incident read experience. Their status lines were corrected to describe the current implementation while retaining the draft approval status and distinguishing disabled authority-gated routes from unconfigured production integrations. The SRS correctly describes itself as a planning baseline.

### Existing OAD Findings

The [existing OAD register](../open_architecture_decisions.md) is a revised draft. Its decision owners are placeholders. This addendum preserves its historical entries and does not mark any OAD approved.

| Existing OAD | Governance finding | Recommended disposition |
|---|---|---|
| OAD-001, OAD-020 | Map provider, display precision, location authority, and correction access remain open. Location model/service support exists, but API reads are disabled. | Keep provider and access decisions unresolved; approve provenance and correction authorities before enabling location endpoints. |
| OAD-002, OAD-014, OAD-016 | Storage provider, media transfer, and retention durations remain undecided. Evidence metadata models exist; no configured provider/verifier enables a usable upload or retrieval workflow. | Keep media private, but defer vendor, transfer contract, retention periods, deletion authority, and legal holds to explicit approval. |
| OAD-005, OAD-012 | AI method remains open. The project owner approved that AI detection never establishes an accident and that only the specifically assigned, authorized human Police reviewer with active membership in the candidate's assigned Police organization may access it. Candidate assignment is by an explicitly authorized authority within that Police organization. | Preserve the approved assignment-scoped boundary. The existing assignment-authority mechanism, candidate-to-organization/reviewer binding, permitted fields, and runtime policy remain unresolved; no whole-group access, global Admin bypass, or new human role. |
| OAD-013, OAD-018, OAD-021 | Assignment creation/reassignment authority and timeout policy remain open. Assignment records and target-scoped response transitions exist; assignment creation has no public route. | Preserve independent target records; approve who can create/reassign and whether/when expiry exists. Do not imply dispatch. |
| OAD-015 | Separate event, candidate, and incident records are implemented. The project owner approved `VERIFIED`, `REJECTED`, and `FURTHER_REVIEW`; only verification creates exactly one atomic `OPEN` incident, while the other outcomes create none and further review preserves the candidate. | Outcome/incident policy slice approved 2026-11-21; event-to-candidate intake/grouping and `FURTHER_REVIEW` runtime support remain unresolved/incomplete. Overall OAD status is unchanged. |
| OAD-017 | AI_SERVICE is a distinct machine actor, but the configured authenticator is absent and intake fails closed. | Keep machine and human identity separate; select and configure the mechanism only after security approval. |
| OAD-019 | Source management authority and input mode remain proposed. | Keep source ownership/consent and registration authority unresolved. |

No separate ADR has been approved ([ADR index](../../decisions/README.md)). The [domain governance decision register](../decisions/domain_governance_decision_register.md) maps proposed dispositions to existing OAD identifiers without creating new OAD numbers.

## Domain Principles

The complete principle set and implementation evidence are in [Domain Principles](domain_principles.md). The controlling boundaries are:

- A `DetectionEvent` is an observation, an `AccidentCandidate` is a review subject, and an `AccidentIncident` is authoritative only after an authorized human verification decision.
- The backend owns identities, authorization, state transitions, and audit. A Flutter role label or UI control cannot grant access.
- Police and Hospital assignments have separate target scope, status, and history. Neither agency may change the other agency's assignment.
- Evidence and precise location are sensitive. Media access must be backend-authorized; camera position must not be presented as accident position.
- Prototype notifications and response representations must remain simulated; no emergency dispatch or real agency delivery is in scope.

These baseline principles are documented in draft requirements and implemented in part. The Police-first workflow and simulation boundaries have since received the scoped project-owner approval recorded below; that does not convert the remaining draft principles or runtime permissions into approved policy.

## Candidate Review Authority

The project owner approved that only the specifically assigned and authorized human Police reviewer with active membership in the candidate's assigned Police organization may review that candidate; candidate assignment must be made by an explicitly authorized authority within that organization. This is not a grant to every `POLICE` user or a global `ADMIN` bypass, and it does not introduce a new human role. The existing backend permission/mechanism for assignment authority and candidate-to-organization/reviewer binding remain unresolved. Hospital and AI_SERVICE cannot review or decide.

The project owner also approved `VERIFIED`, `REJECTED`, and `FURTHER_REVIEW`: only verification creates exactly one atomic linked `OPEN` incident; rejection and further review create none, and further review preserves the candidate for subsequent review. The backend currently models only `RECEIVED → UNDER_REVIEW → VERIFIED | REJECTED`, one final `CandidateReview` per candidate, and required rejection rationale; verification rationale is optional. No reviewer-assignment relation or `FURTHER_REVIEW` command exists, and candidate APIs return policy-unavailable. See [Candidate Review and Verification Policy](candidate_review_verification_policy.md).

## Candidate Verification Authority

Only the specifically assigned and authorized human Police reviewer with active membership in the candidate's assigned Police organization may decide it. AI detection, event association, and reviewer convenience cannot establish an incident. A successful Police verification atomically creates exactly one linked `OPEN` incident. Rejection and `FURTHER_REVIEW` create no incident; further review preserves the candidate for subsequent review. Criteria, rationale policy, permitted fields, and review-count/conflict behavior beyond the approved assigned-reviewer scope remain undecided.

The service already creates the `VERIFIED` review, candidate state, linked `OPEN` incident, initial status history, and success audit within one transaction. Candidate row locking, a unique final-review constraint, a unique incident-per-candidate constraint, and command identifiers protect retries and races. The 2026-11-21 policy confirms exactly one atomic `OPEN` incident on verification and no incident on rejection/further review. The approved Hospital request and simulated response sequence is separately governed and outside candidate review. Candidate assignment authority, candidate-to-organization/reviewer binding, and `FURTHER_REVIEW` implementation remain blockers; APIs stay blocked.

## Rejection and Dismissal Policy

`REJECTED` is an owner-approved outcome that creates no incident. The existing runtime requires a nonblank human rationale; this was not a new policy term in the 2026-11-21 approval. `FURTHER_REVIEW` is the separately approved non-final outcome that creates no incident and preserves the candidate for subsequent review; it is not implemented yet. Do not use “dismissed” as a second terminal meaning or add deletion/reopening without a separate decision.

## Incident Lifecycle

The implemented model is `OPEN → RESPONSE_ACTIVE → RESOLVED → CLOSED`, with `OPEN → RESOLVED` also supported by the domain service. The first agency assignment entering `IN_PROGRESS` changes the incident to `RESPONSE_ACTIVE`; mere acknowledgement does not. Resolve requires a nonblank reason and all assignments in the service's terminal set (`COMPLETED`, `UNABLE_TO_RESPOND`, `CANCELLED`). Close requires `RESOLVED` and a nonblank reason. `EXPIRED` exists as an assignment enum but has no implemented transition and is not in the resolver's terminal set. Reopen is not implemented.

The owner-approved Hospital request and simulated ambulance-response status are not new incident lifecycle states. The existing incident aggregate rule remains separate: acknowledgement alone does not set `RESPONSE_ACTIVE`; any mapping of a Hospital response progression to `IN_PROGRESS` requires a separate explicit decision.

Resolver and closer authority, override handling, and post-closure correction remain unresolved. The draft incident workflow proposes `OPEN → RESOLVED` for a no-response outcome; the current service permits this when the assignment set is empty because the all-terminal guard is vacuously true, but does not require a distinct no-response reason. Resolve and close APIs fail closed. The proposed transition and precondition matrix is in [Incident Lifecycle Policy](incident_lifecycle_policy.md).

## Police and Hospital Independence

An incident may have separate Police and Hospital `ResponseAssignment` records. Matching active organization membership is required for scoped reads and agency actions. The domain model has independent assignment and response histories; a Hospital readiness update does not claim treatment, and a Police progress update does not imply real dispatch. Assignment creation, cancellation, and reassignment authority remain unresolved, and no assignment-creation API route is exposed.

Incident lifecycle is a separate aggregate: an agency action can cause the incident summary to move to `RESPONSE_ACTIVE`, but it does not alter another agency's assignment or automatically resolve/close the incident. Resolution is an incident-level command after all assignments become terminal under the currently implemented guard. OAD-018 should be clarified along these lines when the project team approves its wording.

## Evidence Governance

The recommended baseline is restricted, private media with separately scoped metadata visibility and media retrieval. Require current backend authorization, `AVAILABLE` asset state, integrity/validation, and a per-object access check for every read. Never expose a public bucket, permanent URL, storage credential, or unrestricted object key. Audit successful and denied sensitive access without logging media or credentials. Keep Police and Hospital scopes independent and disclose only approved, minimum-necessary fields.

The repository models `EvidenceAsset`, `EvidenceAssociation`, and upload sessions, including checksum, scan, and lifecycle fields. There is no configured object-storage verifier/provider for an end-to-end workflow; evidence list/detail and upload-session API routes are blocked. Role-specific metadata fields, media access, sharing, retention, legal holds, deletion approvers, and provider choice remain unresolved. Details are in [Evidence Governance Policy](../evidence/evidence_governance_policy.md).

## Location Provenance

The repository distinguishes `CAMERA_POSITION` from `ACCIDENT_LOCATION`; it records source method (`CAMERA`, `GPS`, `INFERRED`, `MANUAL`), optional capture time and accuracy, verification status, and source event/video references. AI_SERVICE may create only an inferred candidate-level accident-location claim. Human create, verify, correct, and read operations require policies. Correction history records prior/new coordinates, accuracy, actor, time, and rationale, while the current row is updated.

Important gaps: externally reported location is not a distinct source method; the model has one current claim per typed subject; there is no policy/API for competing claims or conflict resolution; precise display scope is undecided; and the location API returns 503. OAD-020 and OAD-001 remain open. See [Location Provenance Policy](../location/location_provenance_policy.md).

## Authorization Matrix

The [Authorization Matrix](../security/authorization_matrix.md) lists requested actions by principal, with resource scope, preconditions, policy evidence, current implementation, and approval state. The assigned-reviewer access and assignment-authority boundaries, three outcomes, verified-incident invariant, and auditability are approved policy; runtime candidate routes remain blocked. Incident closure, evidence, and location permissions remain unresolved. Existing code paths that work are implementation evidence, not approval.

## Audit and Security Requirements

Before enabling consequential operations, require authenticated actor identity; current role and object-scope checks; safe 403/404/503 behavior; append-oriented actor/time/action/resource/outcome audit; transactional state plus history plus audit; stable command IDs and database uniqueness for retries; row-lock/state validation for concurrency; safe allow-listed audit context; and no secrets, raw media, signed URLs, or unnecessary personal data in logs.

The audit service allow-lists action codes and context keys. Candidate verification, incident changes, assignment transitions, evidence lifecycle, and location corrections record audit events. Denied operations are audited separately after the failed transaction. The audit stream is not exposed through a public API, and audit retention, integrity protection beyond the database model, and audit-reader scope remain decisions for governance.

## Decision Register

The [Domain Governance Decision Register](../decisions/domain_governance_decision_register.md) captures existing OAD status, options, recommendations, rationale, approval owner class, related requirements/modules, security/domain implications, and implementation impact. OADs are not rewritten or silently approved. No OAD owner is invented; unresolved owners remain the placeholders in the existing register.

## Stakeholder Approvals Required

1. **Project team / requirements owner:** record the 2026-11-21 approved candidate access/assignment boundary and identify the existing backend mechanism that represents assignment authority; resolve the candidate organization/reviewer binding and the minimum permitted response fields. Do not infer checklist, threshold, or rationale rules from this approval.
2. **Relevant Police/Hospital domain representatives:** confirm staffing/scope for the approved Police reviewer role, Hospital target/routing and response-state expectations, evidence fields, incident information, assignment visibility, and that Hospital completion does not imply incident closure. Hospital does not review candidates in the approved workflow.
3. **Source/data owner and institutional privacy/data-governance representative:** approve evidence/location purpose, precision, role access, media retention, deletion authority, legal-hold handling, and evaluation-data reuse.
4. **Project team with backend/security owners:** approve Hospital request creation/routing/recovery, assignment creation/reassignment, incident resolver/closer and override scope, response-state contracts, concurrency/idempotency, machine-auth mechanism, storage provider/access pattern, and audit-read scope.

These are approval roles, not named people. The repository does not identify actual approvers.

## Approved Capabilities

The ADR index still records no approved ADR, and the source OAD status entries remain unchanged. The project owner approved the 2026-11-19 Police-first simulated response sequence and the 2026-11-21 candidate reviewer assignment/access boundaries, three outcomes, atomic verified-incident invariant, and traceable audit requirement. Neither approval enables runtime candidate, Hospital-request, dispatch-status, incident-closure, evidence, location, or machine-ingestion permissions; assignment authority mechanism, candidate binding, intake security, and other detailed contracts remain pending.

The following are current implementation facts, not policy approvals: human JWT authentication; incident summary and assignment reads scoped through active target memberships/assignments; selected target-assignment response commands; distinct domain records; and fail-closed blocked routes. The mobile incident view is read-only.

## Unresolved and Blocked Capabilities

- Candidate access and assignment policy is owner-approved (OAD-012), but queue/detail/review/decision remain blocked until the existing assignment-authority mechanism and candidate organization/reviewer binding are resolved and enforced. `FURTHER_REVIEW` is approved but not implemented; candidate intake remains blocked on OAD-015/017/019.
- Incident resolve/close: blocked by unresolved authority and policy (OAD-012/OAD-018).
- Post-verification Hospital request order is owner-approved; target selection/routing, request/assignment mapping, idempotency/recovery, cancellation/reassignment, and expiry remain unresolved (OAD-013/OAD-018/OAD-021); request-creation route does not exist.
- Hospital acknowledgement and simulated dispatch/status are owner-approved as separate workflow concepts, but the exact status vocabulary, actor grants, and API/history contracts remain unresolved (OAD-018).
- Evidence metadata and media upload/retrieval: blocked by access policy, storage provider/verifier, transfer contract, and retention decisions (OAD-002/OAD-014/OAD-016).
- Location read/create/verify/correct endpoints: blocked by scope, precision, authority, and conflict decisions (OAD-001/OAD-020).
- AI_SERVICE event intake: machine-authenticator unconfigured (OAD-017), therefore fails closed.
- Reopen, dismissal, needs-evidence state, dual review, competing location claims, and real external delivery: not implemented and not approved.

## Implementation Readiness

**Policy readiness: not ready for privileged workflow implementation.** The Police-first sequence has owner approval, but the action-specific authorization and contract decisions required to implement it are incomplete. Preserve fail-closed API behavior until those remaining approvals are recorded. Any new permission or workflow must cite the relevant owner decision and, where required, a separately approved ADR.

Approval, backend policy/API contracts, transaction/concurrency tests, storage and retention design, Flutter workflows, and deployment review are sequenced in [Incident Management Implementation Readiness](implementation_readiness.md). This package itself does not implement those items or run tests.

## Documents Created or Updated

The governance documentation is organized under `docs/architecture/`:

- [Domain Principles](domain_principles.md)
- [Candidate Review and Verification Policy](candidate_review_verification_policy.md)
- [Incident Lifecycle Policy](incident_lifecycle_policy.md)
- [Evidence Governance Policy](../evidence/evidence_governance_policy.md)
- [Location Provenance Policy](../location/location_provenance_policy.md)
- [Authorization Matrix](../security/authorization_matrix.md)
- [Domain Governance Decision Register](../decisions/domain_governance_decision_register.md)
- [Incident Management Implementation Readiness](implementation_readiness.md)
- [Accident Verification and Emergency Response Governance Workflow](accident_verification_emergency_response_workflow.md)
- This architecture decision resolution report.

Updated for current implementation accuracy and discoverability: `docs/architecture/README.md`, `docs/architecture/system_architecture.md`, `docs/architecture/component_architecture.md`, and the addendum link in `docs/architecture/open_architecture_decisions.md`. Existing OAD decisions and statuses remain unchanged.

## Git Diff Summary

The original governance audit began with a clean worktree. The permanent governance documents are now organized by domain under `docs/architecture/`, while the incident-management engineering report is retained under `docs/incident_management/`. This restructuring corrects titles and documentation links only. No backend, Flutter, API, permission, model, migration, or test file was changed for that audit. No tests were run. No commit or push was made.
