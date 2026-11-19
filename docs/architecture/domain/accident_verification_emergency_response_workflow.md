# Accident Verification and Emergency Response Governance Workflow

**Workflow status:** The project owner approved the sequence and safety boundaries in the task input dated 2026-11-19. Detailed authorization scopes, target routing, response-state vocabulary, and runtime contracts remain pending.

**Runtime status:** Documentation only. This approval does not enable a route, permission, provider, notification, or dispatch integration.

**OAD status:** Existing OAD identifiers and status entries are preserved; this document records a scoped owner-approved workflow decision, not blanket closure of related OADs.

**Requirements mapping:** FR-005/019 capture Police verification and atomic incident creation; FR-032 captures the post-verification Hospital request and simulated response scope. The detailed implementation contracts remain pending.

## Purpose and Decision Provenance

This document formalizes the project-owner-approved flow from an AI observation through Police verification to a simulated Hospital request and simulated ambulance-response tracking. The approval is evidenced by the explicit `project_owner_approved_workflow` in the task supplied on 2026-11-19. The project owner's name is not recorded in the repository.

The decision approves the **workflow order and the responsibility boundaries** described below. It does not define which individual Police reviewer is authorized, which Hospital is selected, which data each actor can see, every response-state transition, or how failed request creation is retried. Those remain proposed or unresolved until recorded. This is not a stakeholder approval for real emergency operations.

## Project-Owner-Approved Workflow

| Step | Owner-approved action | Actor and system of record | Result / boundary |
|---|---|---|---|
| 1. AI accident detection | An input is analyzed and the AI service produces a `DetectionEvent`. | AI service submits an observation; Django validates and records authoritative intake. | A detection is an observation only. Source permission, machine authentication, and the accepted event contract remain prerequisites (OAD-017/019). |
| 2. Candidate creation | A possible accident is represented by an `AccidentCandidate`. | Django associates accepted DetectionEvents under an approved grouping rule. | `DetectionEvent`, `AccidentCandidate`, and `AccidentIncident` remain distinct. AI detection alone never creates a verified incident. |
| 3. Police verification | The candidate is routed to an appropriately authorized human Police reviewer, who reviews only permitted information and records a decision under the approved verification policy. | Specifically authorized human Police reviewer; Django checks identity, candidate scope, and state. | Police-first review is approved at the workflow-role level. This is not a grant to every `POLICE` user. Reviewer identity, source/jurisdiction scope, queue/assignment, checklist, decision count, and rationale requirements remain to be recorded. |
| 4. Verified incident creation | On Police confirmation, Django atomically creates exactly one `OPEN` `AccidentIncident`. | Django REST backend is authoritative. | Duplicate creation is prevented. A rejected or inconclusive candidate creates no incident. An inconclusive candidate remains under review unless a later approved policy defines another state. |
| 5. Hospital response request | After successful Police verification and incident creation, the system creates a request for the designated Hospital. | Backend-created request linked to the verified incident; the Hospital is an independent target. | The request must not precede or exist without the verified incident. Target selection/routing and request-to-`ResponseAssignment` mapping remain unresolved. The request is simulated and in-app only. |
| 6. Hospital acknowledgement | An authorized Hospital user records acknowledgement and availability or inability to respond. | Human Hospital user with active matching Hospital membership and scope to the request. | Request acknowledgement, available/unavailable response, and dispatch decision are distinct facts. Exact fields and allowed state transitions remain pending. |
| 7. Ambulance response | The Hospital records a simulated ambulance-dispatch decision and subsequent response status. | Authorized Hospital user; Django persists the simulated decision and history. | Dispatch decision and subsequent status are separate from request acknowledgement. No real ambulance is contacted or dispatched. Exact status vocabulary and transition authority remain pending. |
| 8. Response tracking | Authorized users track the incident and Hospital response independently. | Backend-scoped readers; Police and Hospital access remain separately scoped. | No user gets global access by role name. The Police review view, Hospital request view, Admin oversight, exposed fields, and location/evidence visibility still require explicit scope decisions. |

~~~mermaid
sequenceDiagram
    participant Source as Authorized demo source
    participant AI as AI_SERVICE
    participant API as Django backend
    participant Police as Authorized Police reviewer
    participant Hospital as Authorized Hospital user
    Source->>AI: Synthetic or expressly authorized input
    AI->>API: DetectionEvent with source/event provenance
    API->>API: Validate, deduplicate, create/associate AccidentCandidate
    Police->>API: Review permitted candidate information
    alt Police rejects or cannot conclude
        API->>API: Record REJECTED or retain UNDER_REVIEW
        Note over API,Hospital: No AccidentIncident and no Hospital request
    else Police verifies
        API->>API: Atomic candidate decision and one OPEN AccidentIncident
        API->>API: Create linked, simulated Hospital request after incident commit
        Hospital->>API: Record acknowledgement and availability or inability
        Hospital->>API: Record separate simulated dispatch decision
        Hospital->>API: Record subsequent simulated response status
        Note over API,Hospital: Each update is scoped, traceable, and simulated
    end
~~~

The sequence diagram expresses the approved workflow order. The durable request mechanism, event/outbox design, and retry contract are proposals for implementation review, not approved technical decisions.

## Status and Record Semantics

### Approved semantics

- Django REST Framework is the authoritative decision and state boundary; clients and AI submit observations or authorized commands.
- The three domain entities have separate meanings. A DetectionEvent is not a candidate decision; a candidate is not an incident; only authorized Police verification creates an authoritative incident.
- Police verification must precede Hospital request creation. No request follows a rejection or an inconclusive review.
- Candidate verification and creation of one `OPEN` incident must be atomic and duplicate-safe.
- Hospital request acknowledgement, Hospital availability/inability, simulated ambulance-dispatch decision, and subsequent simulated response status are distinct events.
- Police and Hospital scopes remain independent; all consequential decisions and transitions must be auditable.
- Use synthetic or expressly authorized test events. All notifications, acknowledgements, dispatch decisions, and response outcomes are simulated. No external police, hospital, ambulance, or emergency-number communication is permitted.

### Proposed technical mapping and pending details

The existing domain has `ResponseAssignment`, `Response`, and separate histories. A reasonable mapping is one Hospital-target `ResponseAssignment` for the response request, with acknowledgement/unable-to-respond recorded against that target and a separate Hospital response record for simulated dispatch and subsequent status. **This mapping is a proposal**, because the owner approved the workflow behavior but did not approve exact model/API representation or status vocabulary.

Do not collapse these into one ambiguous `ACKNOWLEDGED` or `DISPATCHED` state. Do not infer a specific “en route,” “arrived,” or “completed” status from the approval; those labels, transition rules, actor authority, cancellation behavior, and whether dispatch can be declined are open. Do not add an `AccidentIncident` status for ambulance activity. Incident lifecycle and Hospital response status remain independent.

The existing incident policy sets `RESPONSE_ACTIVE` when the first assignment enters `IN_PROGRESS`, not at acknowledgement. The task does not change that rule. If a Hospital response is modeled through the existing assignment lifecycle, the team must decide which Hospital action (if any) is an `IN_PROGRESS` event before implementation; acknowledgement alone must not activate the incident.

## Authorization, Evidence, and Location Boundaries

| Principal | Approved workflow responsibility | Required guard / still pending |
|---|---|---|
| `AI_SERVICE` | Submit a detection observation and supporting provenance. | Separate machine identity only; no candidate review, verification, incident creation, Hospital request, response update, or general evidence read. OAD-017 authenticator and OAD-019 source authorization remain unresolved. |
| `POLICE` | A specifically authorized human Police reviewer reviews the candidate and records the verification decision. | Police reviewer role class/order is owner-approved. Individual identity, candidate/source/jurisdiction scope, queue/assignment, number of reviewers, permitted fields, evidence checklist, criteria, rationale, and permission checks remain unresolved under OAD-012. `POLICE` group membership alone must not grant review. |
| `HOSPITAL` | An authorized Hospital user records request acknowledgement, availability/inability, simulated dispatch decision, and subsequent response status. | Active membership in the exact Hospital organization and assignment/request scope; no Police data or other Hospital target scope. Selection/routing, response-status permissions, and visible fields require approval. |
| `ADMIN` | No additional authority is implied by this workflow. | No global candidate, incident, Hospital, evidence, location, or audit access. Any oversight requires a separate explicit policy. |

Candidate review information is limited to what the approved verification policy permits. This workflow does not approve media or location access. Evidence metadata and media remain separately authorized and blocked under OAD-002/014/016; location read/precision/correction remain separately gated under OAD-001/020. If a reviewer cannot lawfully or safely access required information, the candidate stays under review; do not widen access to make the workflow appear complete.

Hospital request and response details must be minimized to the approved purpose. The workflow itself does not settle whether Police can view Hospital response details, whether Admin can oversee either organization, or whether precise accident location is shown to Hospital users.

## Failure, Duplicate, and Recovery Handling

The first column below follows the owner-approved outcome. Where the handling mechanism was not specified, it is marked as a recommended default requiring implementation review.

| Failure or edge case | Required outcome | Audit and recovery |
|---|---|---|
| Unauthorized/revoked source or invalid AI_SERVICE | Reject before candidate or incident mutation; fail closed. | Record safe service/source identifiers and denial reason; never log credentials or raw media. Correct authorization and retry only with stable event identity. |
| AI processing failure, no observation, or unavailable backend | Do not create a verified incident or Hospital request. | Keep processing failure distinct from a completed no-observation result. Retry the same event identity after an unknown backend outcome. |
| Duplicate DetectionEvent submission | Same identity and payload returns/reuses the prior intake result; it must not create duplicate event/candidate/request/incident records. | Record an idempotent outcome. Same event identity with conflicting payload must be rejected as a conflict. |
| Similar but distinct events | Do not silently merge or discard provenance. Candidate association is governed by a separately approved grouping rule. | Until that rule exists, preserve events separately or flag uncertain grouping for authorized human handling. |
| Police reviewer is unauthorized or outside candidate scope | Deny without changing candidate state or disclosing out-of-scope data. | Record actor, action, candidate reference where safe, outcome, time, request/command ID, and a safe reason code. |
| Candidate is inconclusive or evidence is missing/contradictory | Keep `UNDER_REVIEW`; create neither incident nor Hospital request. | Record an attributable pending reason under the approved review policy. Do not invent a `NEEDS_EVIDENCE` state. |
| Police rejects candidate | Set `REJECTED` under the approved candidate policy; create no incident and no Hospital request. | Keep decision/rationale and provenance under the approved retention policy. No automatic reopen. |
| Verification/incident transaction fails or races | Commit neither a partial verification nor an orphan/duplicate incident. | Retry the same command idempotently; a conflicting final command fails stale/conflict. Candidate decision, incident, histories, and success audit commit atomically. |
| Hospital target is absent, inactive, or routing is ambiguous | Do not create a request to an arbitrary target. The verified incident remains `OPEN`; request-generation outcome is visible to an authorized operator. | Recommended: record a pending/failed request-generation outcome and allow a safe, idempotent retry after target configuration is corrected. Target selection/authority remains OAD-013. |
| Hospital request creation fails after incident commit | Do not roll back or duplicate the verified incident. Do not report the Hospital as notified. | Recommended: persist a retryable request outcome linked to the incident; retry idempotently and audit attempts. Exact outbox/worker/API design remains OAD-008/011 and must be approved. |
| Duplicate verification or request retry | Keep exactly one verified incident per candidate and at most one active request per incident/designated Hospital unless an approved replacement rule exists. | Reuse command/idempotency identity; record conflicts and never create a second incident or silently reroute. The active-request uniqueness detail is a proposed guard. |
| Hospital acknowledgement or availability update is unauthorized/stale | Reject without changing Hospital or incident state. | Scope to the active Hospital membership and exact target request; audit the denial and preserve prior assignment/response history. |
| Hospital records inability to respond | Record inability for that Hospital request. Do not infer ambulance dispatch, alter Police state, or silently route to a second Hospital. | Any alternate-target selection/reassignment is a separate OAD-013 decision and must be explicit, authorized, and audited. |
| Simulated dispatch decision is declined, fails, or remains unknown | Record only the simulated outcome that the Hospital actor actually selected; never display a real dispatch confirmation. | Exact statuses and follow-up rules are pending. No automatic emergency call, retry to an external endpoint, or inferred ambulance movement. |
| Hospital response update conflicts with another request or actor | Deny stale/conflicting command; do not overwrite another target’s history. | Use per-request command IDs, state preconditions, transaction locks, and separate response history. |
| Evidence/location unavailable to reviewer or Hospital | Do not widen role scope or fabricate values. Continue review only with approved information; otherwise leave candidate pending or show unavailable. | Preserve evidence and location confidentiality, provenance, and separate access audits. |
| Notification delivery failure | Keep the request and delivery outcome distinct; mark delivery simulated/unavailable according to the approved prototype contract. | No real push, phone call, police/hospital contact, or ambulance dispatch fallback. |

## Audit Requirements

For every accepted decision or response transition, record the authenticated human or machine actor, action, target/request/candidate/incident identifiers, prior and resulting state where applicable, UTC time, outcome, request/command ID, and safe reason code. The candidate decision’s rationale belongs in the protected review record. Hospital availability/inability and simulated dispatch decision/status must be separately attributable.

Keep Police review history separate from Hospital response history. Do not put video, credentials, tokens, signed URLs, raw request bodies, unnecessary personal information, or full-precision coordinates in general audit/log context. Audit-reader scope and retention remain unresolved. Denials and invalid transitions must be safely auditable without revealing out-of-scope incident or evidence existence.

## Decisions Still Pending

| Decision | Current owner-approved scope | Still unresolved / related OAD |
|---|---|---|
| Police reviewer authorization | Police-first review by an appropriately authorized human. | Named reviewer/group, source/jurisdiction scope, review assignment/claim, one versus multiple reviewers, permitted fields, checklist, rationale, and conflict/revision rules (OAD-012, OAD-005). |
| Candidate/event grouping | Separate observation, candidate, and incident; inconclusive/rejected candidates do not create incidents. | Similar-event association, duplicate-candidate handling, and explicit review assignment contract (OAD-015, OAD-008). |
| Hospital target and request authority | Backend creates a Hospital request only after verified incident creation; request links to that incident. | Who designates the Hospital; eligibility/jurisdiction; automatic versus configured routing; replacement/alternate target; mapping to `ResponseAssignment`; request idempotency and recovery (OAD-013, OAD-018, OAD-011). |
| Hospital acknowledgement/availability | Authorized Hospital user records acknowledgement and availability or inability. | Exact data fields, assignment transitions, reason requirements, and ability to update after acknowledgement (OAD-018). |
| Simulated ambulance response | Hospital records a simulated dispatch decision and subsequent response status, separate from request acknowledgement. | Status vocabulary, transitions, authority, cancellation, timing, and client labels. No real dispatch (OAD-007; OAD-018). |
| Incident aggregate status | Existing proposal: acknowledgement alone does not change incident; first assignment `IN_PROGRESS` may set `RESPONSE_ACTIVE`. | Whether Hospital simulated response progression maps to `IN_PROGRESS`; do not change incident status semantics without an explicit decision (OAD-018). |
| Evidence and location | Only approved review information may be shown. | Provider, fields/media scope, Hospital access, location origin/precision/conflict/correction, retention, and legal hold (OAD-001/002/014/016/020). |
| Source and machine identity | AI submits observations only; backend authorizes all state changes. | Source consent/registration, machine authentication/rotation/replay, deployment contract (OAD-017/019/008). |
| Incident resolution and timeout | Not defined by this workflow. | Resolver/closer, zero-assignment outcome, terminal assignment set, overrides, reopening, timeout/`EXPIRED` (OAD-012/018/021). |

## Phase Placement

No approved Phase 5E plan was found in the repository. The following allocation is a **proposed milestone boundary** for project-owner scheduling; it does not make a pending policy or OAD approved.

### Proposed Phase 5E scope, after the listed decisions are recorded

- Controlled synthetic or expressly authorized event intake with approved source and separate machine identity.
- Police-only candidate review by specifically designated reviewers, with the approved information fields and verification criteria.
- Idempotent, atomic candidate decision and single `OPEN` incident creation; rejected/inconclusive paths produce no incident or Hospital request.
- Post-commit creation of an incident-linked request for the explicitly designated Hospital, with idempotency, audit, and recoverable failure handling.
- Hospital-scoped acknowledgement and availability/inability record.
- Distinct simulated ambulance-dispatch decision and subsequent simulated response status, under a status contract approved before implementation.
- Role/organization-scoped incident and Hospital response tracking; audit of all decisions and transitions; an end-to-end no-external-contact safety check.

### Later or separately gated milestones

- Evidence storage provider, media upload/retrieval, sharing, retention/deletion, and legal-hold workflows (OAD-002/014/016).
- Precise location collection/display, map provider, external-report origin, competing claims, and correction workflow (OAD-001/020).
- Automated Hospital selection/routing, alternative-Hospital reassignment, timers, expiry, and any automatic follow-up (OAD-011/013/021).
- Production deployment, live camera integrations, real provider credentials, and advanced model/tracking claims (OAD-003/004/006/009).
- Real police/hospital/ambulance/emergency-service delivery is **out of scope for this academic prototype**, not a later milestone in this plan.

## Testable Acceptance Criteria

These criteria are for future implementation validation; no code or tests are changed by this document.

1. A valid DetectionEvent creates or associates a distinct candidate; machine identity cannot make a Police decision or create an incident.
2. Only a specifically authorized Police reviewer in the approved source/jurisdiction scope can inspect and finalize the candidate. Other Police users, Hospital users, Admin users without explicit grants, and AI_SERVICE are denied.
3. Rejected and inconclusive candidates create no incident and no Hospital request. An inconclusive candidate remains reviewable under the approved policy.
4. A Police verification commits the candidate decision and exactly one linked `OPEN` incident atomically. Concurrent verification and identical retries create no duplicate incident; a failed transaction leaves no partial result.
5. A Hospital request is created only after the incident commit, is linked to that incident and the approved Hospital target, and is idempotent on retry. A failed request attempt does not falsely claim delivery or duplicate the incident.
6. Only a current authorized member of the designated Hospital organization can acknowledge or record availability/inability for that request. Hospital updates cannot change Police review history or another Hospital target’s state.
7. Request acknowledgement is observably distinct from availability/inability, simulated dispatch decision, and subsequent simulated response status. No acknowledgement implies dispatch; no simulated status is presented as real.
8. Authorized tracking exposes only approved fields and the user’s assigned organization scope. Admin has no global bypass. Out-of-scope reads are concealed consistently.
9. Each candidate decision, request creation/attempt, acknowledgement, availability/inability, simulated dispatch decision, response status update, and denial records actor, target, time, outcome, and command/request ID with safe audit context.
10. Synthetic or expressly authorized events can exercise success, rejection, inconclusive, duplicate, unavailable Hospital, request failure/retry, stale update, and simulated dispatch failure paths.
11. An end-to-end safety scenario verifies that the system makes no network call, phone call, push delivery, or other contact to real Police, Hospital, ambulance, or emergency-service systems.
12. Evidence and location remain unavailable unless their separate OAD decisions and role-specific grants are approved; missing values remain unknown and do not block safety by being fabricated.

## Related Documentation

- [Candidate Review and Verification Policy](candidate_review_verification_policy.md)
- [Incident Lifecycle Policy](incident_lifecycle_policy.md)
- [Authorization Matrix](../security/authorization_matrix.md)
- [Domain Governance Decision Register](../decisions/domain_governance_decision_register.md)
- [Implementation Readiness](implementation_readiness.md)
- [Evidence Governance Policy](../evidence/evidence_governance_policy.md)
- [Location Provenance Policy](../location/location_provenance_policy.md)
- [Open Architecture Decisions](../open_architecture_decisions.md)
- [Functional Requirements](../../requirements/functional_requirements.md)
- [Requirements Traceability](../../requirements/requirements_traceability.md)
