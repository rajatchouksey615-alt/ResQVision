# Incident Management Implementation Readiness

**Readiness:** The project owner has approved the conceptual Police-first verification and simulated Hospital response sequence, but detailed permissions/contracts remain incomplete and privileged implementation is not yet ready.
**Report status:** `PARTIALLY_RESOLVED`; this document is an approval gate and sequencing proposal, not authorization to change runtime permissions.

## Owner-Approved Workflow Scope (2026-11-19)

The project owner explicitly approved this order: a specifically authorized human Police reviewer verifies a candidate; a successful verification atomically creates one linked `OPEN` incident; only after that incident is committed does the backend create a linked request for the designated Hospital; an authorized Hospital user records acknowledgement and availability/inability; and the Hospital records a separate simulated ambulance-dispatch decision and subsequent simulated response status. Rejected/inconclusive candidates create neither an incident nor a Hospital request. All response and notification activity remains simulated and no real emergency service is contacted. See the [Accident Verification and Emergency Response Governance Workflow](accident_verification_emergency_response_workflow.md).

This approval fixes workflow order and role classes, not individual user grants. Candidate reviewer identity/scope/criteria, Hospital selection and routing, request-to-assignment mapping, response state vocabulary, visible fields, and failure/retry contract remain unresolved. It does not enable APIs or override OAD status entries.

## Capability Inventory

| Capability | Existing evidence | Readiness |
|---|---|---|
| Human authentication and active-account checks | JWT authentication, active-user checks, profile API. | Implemented runtime capability; source documents remain draft. |
| Incident summary and assignment reads | Scoped querysets require active target organization/membership and active assignment; concealed out-of-scope detail is 404. | Available as read-only behavior; no global Admin scope. |
| Agency assignment updates | Services support acknowledge, start/activity, unable-to-respond, and completion with membership/state checks and command IDs. | Existing service/API behavior. Hospital acknowledgement/availability is owner-approved at workflow level; exact request/state mapping and runtime scope remain pending. |
| Candidate review and verification | Domain model/service supports review, verify/reject, atomic incident creation, audit, unique constraints. | Workflow role/order approved for a specifically authorized Police reviewer; blocked until identity, candidate scope, permitted fields, review assignment, criteria, and rationale are recorded. Candidate endpoints remain 503. |
| Incident resolve/close | Domain services implement state/reason/all-assignment guards and idempotency. | Blocked: endpoints return 503; resolver/closer authority unresolved. |
| Assignment create/cancel/reassign | Domain service hooks exist for creation and reassignment; cancellation service exists. | Post-verification Hospital request is owner-approved, but target selection/routing and request-to-assignment mapping are unresolved. No creation API; cancellation/reassignment remain blocked. |
| Hospital simulated response | Current domain has target-scoped assignment/response records; no separate simulated dispatch contract is approved or enabled. | Workflow semantics approved: acknowledgement, availability/inability, simulated dispatch decision, and subsequent response status are distinct. Exact states, actor actions, request API, and audit/history contract remain blocked. |
| Assignment expiry | Enum value and schema vocabulary exist. | Not implemented: no transition, timer, worker, or approved timeout policy. |
| Evidence upload/retrieval | Models and lifecycle coordination exist; integrity constraints are present. | Blocked: no configured provider/verifier; metadata/media routes and upload sessions unavailable. |
| Location create/verify/correct/read | Typed models and policy-gated domain service functions exist. | Blocked: role/scope policy unresolved; location API returns 503; conflict/external-source gaps remain. |
| AI_SERVICE intake | Separate machine actor/authentication adapter contract exists. | Blocked: authenticator is unconfigured under OAD-017; service intake fails closed. |
| Live dispatch/agency notification | No prototype support is intended. | Prohibited by prototype safety boundary. |

Implementation evidence is not stakeholder approval. The current fail-closed responses must remain until approval is recorded.

## Approval Gate

Before enabling candidate, incident, evidence, location, or assignment-management operations, record approvals for:

1. Police reviewer identity/group, candidate/source/jurisdiction scope, review assignment, number of reviewers, permitted information, checklist, rationale, and rejection/revision semantics. The Police-first role/order itself is approved.
2. Hospital designation/routing/eligibility, request-to-assignment mapping, request idempotency/recovery, Hospital acknowledgement and availability/inability fields, simulated dispatch/status vocabulary, and authorized tracking scope.
3. Incident resolver/closer authority, no-assignment outcome, override scope, reopening/invalidity policy, and terminal assignment rule including `EXPIRED`.
4. Assignment creation/cancellation/reassignment authority, target eligibility, non-acknowledgement policy, and any simulated overdue indicator. The post-verification Hospital request trigger is approved; target choice remains open.
5. Evidence classification, role-specific metadata/media scope, provider/transfer/retrieval design, integrity/scanning criteria, retention, legal hold, deletion approver, and audit-reader scope.
6. Location claim owners/origins, precision/display scope, external-report provenance, competing claims, correction authority, and history retention.
7. AI machine-auth mechanism, credential lifecycle, replay/rate limits, narrowly scoped capabilities, source authorization, and safe failure behavior.

Approval record must identify decision owner, approving role/person, date, status, rationale, related OAD/requirements, and implementation consequences. Do not mark code behavior or this recommendation as approval.

## Recommended Implementation Sequence After Approval

| Sequence | Work item | Preconditions / exit condition |
|---|---|---|
| 1 | Record accepted OAD amendments/ADRs and update requirement status. | Named owners approve authority and data policy; decisions are traceable. |
| 2 | Convert approvals into explicit backend policies and action-specific API contracts. | Every action has actor, resource scope, preconditions, denial behavior, and safe audit fields. |
| 3 | Implement backend workflow contracts and any necessary schema changes. | Transaction boundaries, idempotency, locking, history, and migration needs reviewed. No new states are added before their business meaning is approved. |
| 4 | Implement evidence provider adapter and retention/reconciliation workers. | Provider, upload/retrieval mechanism, validation, scanning, deletion, retention, and recovery are approved. |
| 5 | Implement location claim conflict/correction/display contract. | Origin categories, precision, scope, conflict resolution, and history semantics are approved. |
| 6 | Add Flutter review/incident/evidence/location screens. | API contracts and role-specific data fields are stable; client remains presentation-only for authorization. |
| 7 | Verify test and security coverage before enabling operationally sensitive paths. | Authorization matrix positive/negative tests, cross-organization isolation, transaction rollback, race/idempotency, audit completeness, privacy/log redaction, retention/deletion recovery, and prototype-safety checks pass. |
| 8 | Deployment and operational review. | AI credentials, storage privacy, backup/recovery, access review, monitoring, and environment-specific security controls are approved. |

## Testing Requirements for Future Implementation

Tests should prove that: only specifically authorized Police reviewers can inspect/decide candidates; unauthorized roles cannot inspect candidate/evidence/location; active membership and request/assignment scope are enforced on each request; out-of-scope reads are concealed consistently; unresolved policy never grants access; concurrent Police verification creates at most one incident; transaction failure commits neither decision nor incident; Hospital request creation occurs only after incident commit and retries idempotently; Hospital acknowledgement, availability/inability, simulated dispatch decision, and response status are distinct; Hospital updates cannot change Police review or other target histories; notification/read state never acknowledges a request; `EXPIRED` is unusable until timeout policy is active; evidence is unavailable until validated and inaccessible after expiry; location source/uncertainty and correction history survive writes; audit events include actor/outcome without sensitive payload; and no prototype action sends a real notification/dispatch.

These are future acceptance criteria. No tests were run for this documentation-only task.

## Proposed Phase 5E Scope

The repository does not contain an approved Phase 5E plan. The following is a proposed milestone allocation based on the owner-approved workflow, subject to the detailed decisions above:

1. Use synthetic or expressly authorized test input with a separately authenticated AI_SERVICE and approved source.
2. Implement a candidate queue restricted to specifically authorized Police reviewers; record verification, rejection, and inconclusive outcomes under the approved criteria.
3. Atomically create exactly one `OPEN` incident only on successful Police verification.
4. After incident commit, create one linked request for the explicitly designated Hospital, with idempotent retry and visible failure outcome.
5. Let the scoped Hospital user acknowledge and record availability/inability, then record a separate simulated dispatch decision and subsequent simulated response status.
6. Provide only approved role/organization-scoped tracking and audit history; test that no external contact or real dispatch can occur.

The response status contract, hospital target/routing, and reviewer scopes must be approved before their implementation. Evidence media, location display, live video provider integrations, automated routing/timers, and deployment with retained sensitive data are later or separately gated work. Real emergency-service integration is out of scope for this academic prototype.

## Current Blockers and Dependencies

- OAD-012's role/order is partly settled by the owner-approved Police-first workflow; reviewer identity, scope, criteria, and runtime grant still block candidate queue/review/verification/rejection. Incident resolve/close remains blocked.
- OAD-013/OAD-018's post-verification Hospital request sequence is partly settled; target selection, request/assignment contract, dispatch/status transitions, cancellation, and reassignment remain blocked.
- OAD-002/OAD-014/OAD-016 block complete evidence storage/retrieval and lifecycle operation.
- OAD-001/OAD-020 block location access/display and authority.
- OAD-017 blocks AI_SERVICE intake because no authenticator is configured.
- OAD-021 blocks expiry behavior; the model enum alone does not provide a transition.
- Current requirements and OAD documents remain revised drafts; the project-owner workflow decision is recorded, but the detailed action-policy approvals and formal OAD/ADR disposition remain outstanding.

Until those blockers are resolved, incident management policy readiness remains partial and privileged workflows are not ready to enable.
