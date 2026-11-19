# Domain Governance and Architecture Decision Resolution

Domain Governance and Policy Review

**Status: PARTIALLY_RESOLVED**  
**Approval package:** Ready for project-team and domain-stakeholder review  
**Scope:** Repository audit and documentation only. No code, permission, schema, migration, or runtime-policy changes were made.

## Executive Summary

ResQVision already has a useful separation between AI observations, candidates, verified incidents, agency assignments, evidence metadata, and location claims. Django services and database constraints implement several integrity controls, including transactional candidate verification, independent agency assignment records, scoped incident reads, append-oriented audit records, and fail-closed policy hooks.

The governance baseline is not approved. The SRS, requirements, workflows, role-permission matrix, architecture, and OAD register are marked `REVISED_DRAFT` or proposed. Existing code is evidence of current behavior, not evidence that the team or an agency approved that behavior. No candidate-review, verification, incident-resolution, evidence-access, or location-access permission is treated as approved here.

The main recommendation is to keep privileged operations unavailable until named decision owners approve the authority and scope policies recorded below. Preserve the existing fail-closed behavior while those decisions are pending. This overview and its supporting policy and register documents form the domain governance package.

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
| OAD-005, OAD-012 | AI verification method and human review authority are distinct open decisions. Requirements prohibit AI-only verification, but do not approve which humans may decide. | Preserve human-only final authority as a requirement-level draft principle; approve reviewer role, scope, criteria, and decision count before enabling review. |
| OAD-013, OAD-018, OAD-021 | Assignment creation/reassignment authority and timeout policy remain open. Assignment records and target-scoped response transitions exist; assignment creation has no public route. | Preserve independent target records; approve who can create/reassign and whether/when expiry exists. Do not imply dispatch. |
| OAD-015 | Separate event, candidate, and incident records are recommended and implemented in the schema/services. | Retain the separation recommendation; code does not approve it as policy. |
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

These are documented in draft requirements and implemented in part. They are not represented as organizationally approved policy.

## Candidate Review Authority

The recommended model is an explicitly authorized human reviewer cohort with explicit candidate/resource scope, separate review and final-decision permissions, and no privilege inferred from `ADMIN`, `POLICE`, or `HOSPITAL` membership alone. `ADMIN` is one option in the existing requirements, not a blanket reviewer grant. Police and Hospital receive no candidate-review access by default. AI_SERVICE cannot review or decide.

The backend currently models `RECEIVED → UNDER_REVIEW → VERIFIED | REJECTED`, one final `CandidateReview` per candidate, and required rationale for rejection. Verification rationale is optional in code. There is no reviewer-assignment entity, no `NEEDS_EVIDENCE` state, no dismissal state, and no reopen/re-review path. Candidate APIs currently return policy-unavailable responses. See [Candidate Review and Verification Policy](candidate_review_verification_policy.md).

## Candidate Verification Authority

Only an explicitly authorized human may verify a candidate; AI confidence, event association, and reviewer convenience cannot establish an incident. The recommended MVP decision rule is one authorized human final decision, with a documented evidence/provenance checklist and a nonblank rationale for either outcome. This recommendation and whether a second independent decision is needed require approval by the project team and relevant domain stakeholders.

The service already creates the `VERIFIED` review, candidate state, linked `OPEN` incident, initial status history, and success audit within one transaction. Candidate row locking, a unique final-review constraint, a unique incident-per-candidate constraint, and command identifiers protect retries and races. This service is not reachable through an enabled review API while OAD-012 is unresolved.

## Rejection and Dismissal Policy

Recommend one nonterminal-to-final rejection outcome named `REJECTED`, with a required human rationale and retained candidate provenance under an approved retention policy. Do not use “dismissed” as a second terminal meaning until the team defines a distinct business purpose and audit/reporting behavior. Do not silently treat insufficient evidence as rejection: keep the candidate under review and make the limitation visible. No candidate deletion, dismissal, or reopening is currently approved or implemented.

## Incident Lifecycle

The implemented model is `OPEN → RESPONSE_ACTIVE → RESOLVED → CLOSED`, with `OPEN → RESOLVED` also supported by the domain service. The first agency assignment entering `IN_PROGRESS` changes the incident to `RESPONSE_ACTIVE`; mere acknowledgement does not. Resolve requires a nonblank reason and all assignments in the service's terminal set (`COMPLETED`, `UNABLE_TO_RESPOND`, `CANCELLED`). Close requires `RESOLVED` and a nonblank reason. `EXPIRED` exists as an assignment enum but has no implemented transition and is not in the resolver's terminal set. Reopen is not implemented.

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

The [Authorization Matrix](../security/authorization_matrix.md) lists all requested actions by principal, with resource scope, preconditions, evidence, recommended permission, current implementation, status, and approver. Its key conclusion is that no candidate, verification, incident closure, evidence, or location access permission is approved by current repository artifacts. Existing code paths that work are labeled implementation evidence only.

## Audit and Security Requirements

Before enabling consequential operations, require authenticated actor identity; current role and object-scope checks; safe 403/404/503 behavior; append-oriented actor/time/action/resource/outcome audit; transactional state plus history plus audit; stable command IDs and database uniqueness for retries; row-lock/state validation for concurrency; safe allow-listed audit context; and no secrets, raw media, signed URLs, or unnecessary personal data in logs.

The audit service allow-lists action codes and context keys. Candidate verification, incident changes, assignment transitions, evidence lifecycle, and location corrections record audit events. Denied operations are audited separately after the failed transaction. The audit stream is not exposed through a public API, and audit retention, integrity protection beyond the database model, and audit-reader scope remain decisions for governance.

## Decision Register

The [Domain Governance Decision Register](../decisions/domain_governance_decision_register.md) captures existing OAD status, options, recommendations, rationale, approval owner class, related requirements/modules, security/domain implications, and implementation impact. OADs are not rewritten or silently approved. No OAD owner is invented; unresolved owners remain the placeholders in the existing register.

## Stakeholder Approvals Required

1. **Project team / requirements owner:** confirm the draft requirements and approve candidate reviewer scope, one- versus multi-reviewer decision count, verification checklist, rejection semantics, and whether verification rationale is mandatory.
2. **Relevant Police/Hospital domain representatives:** confirm whether either agency needs candidate review, evidence fields, incident information, assignment visibility, and whether agency completion should only inform incident review.
3. **Source/data owner and institutional privacy/data-governance representative:** approve evidence/location purpose, precision, role access, media retention, deletion authority, legal-hold handling, and evaluation-data reuse.
4. **Project team with backend/security owners:** approve assignment creation/reassignment, incident resolver/closer and override scope, concurrency/idempotency contracts, machine-auth mechanism, storage provider/access pattern, and audit-read scope.

These are approval roles, not named people. The repository does not identify actual approvers.

## Approved Capabilities

No business policy in the reviewed document set is marked approved: the governing requirements and OAD register are drafts, and there is no approved ADR. This means **no candidate, verification, incident closure, evidence, location, or machine-ingestion authority is claimed as policy-approved**.

The following are current implementation facts, not policy approvals: human JWT authentication; incident summary and assignment reads scoped through active target memberships/assignments; selected target-assignment response commands; distinct domain records; and fail-closed blocked routes. The mobile incident view is read-only.

## Unresolved and Blocked Capabilities

- Candidate queue/detail, event association, review, verification, rejection: blocked by unresolved reviewer authority (OAD-012).
- Incident resolve/close: blocked by unresolved authority and policy (OAD-012/OAD-018).
- Assignment creation, cancellation, reassignment, expiry: authority unresolved (OAD-013/OAD-018/OAD-021); creation has no route.
- Evidence metadata and media upload/retrieval: blocked by access policy, storage provider/verifier, transfer contract, and retention decisions (OAD-002/OAD-014/OAD-016).
- Location read/create/verify/correct endpoints: blocked by scope, precision, authority, and conflict decisions (OAD-001/OAD-020).
- AI_SERVICE event intake: machine-authenticator unconfigured (OAD-017), therefore fails closed.
- Reopen, dismissal, needs-evidence state, dual review, competing location claims, and real external delivery: not implemented and not approved.

## Implementation Readiness

**Policy readiness: not ready for privileged workflow implementation.** Preserve fail-closed API behavior until approvals are recorded. Noncontroversial engineering safeguards can be planned, but any new permission or workflow must cite the resulting approval and, where required, a separately approved ADR.

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
- This architecture decision resolution report.

Updated for current implementation accuracy and discoverability: `docs/architecture/README.md`, `docs/architecture/system_architecture.md`, `docs/architecture/component_architecture.md`, and the addendum link in `docs/architecture/open_architecture_decisions.md`. Existing OAD decisions and statuses remain unchanged.

## Git Diff Summary

The original governance audit began with a clean worktree. The permanent governance documents are now organized by domain under `docs/architecture/`, while the milestone-specific engineering report is retained under `docs/incident_management/`. This restructuring corrects titles and documentation links only. No backend, Flutter, API, permission, model, migration, or test file was changed. No tests were run. No commit or push was made.
