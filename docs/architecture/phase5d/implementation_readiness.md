# Phase 5D Implementation Readiness

**Readiness:** Policy decisions are not ready for privileged workflow implementation.  
**Report status:** `PARTIALLY_RESOLVED`; this document is an approval gate and sequencing proposal, not authorization to change runtime permissions.

## Capability Inventory

| Capability | Existing evidence | Readiness |
|---|---|---|
| Human authentication and active-account checks | JWT authentication, active-user checks, profile API. | Implemented runtime capability; source documents remain draft. |
| Incident summary and assignment reads | Scoped querysets require active target organization/membership and active assignment; concealed out-of-scope detail is 404. | Available as read-only behavior; no global Admin scope. |
| Agency assignment updates | Services support acknowledge, start/activity, unable-to-respond, and completion with membership/state checks and command IDs. | Existing service/API behavior; full agency workflow authority remains governed by draft requirements. |
| Candidate review and verification | Domain model/service supports review, verify/reject, atomic incident creation, audit, unique constraints. | Blocked: candidate endpoints return 503 and OAD-012 is unresolved. |
| Incident resolve/close | Domain services implement state/reason/all-assignment guards and idempotency. | Blocked: endpoints return 503; resolver/closer authority unresolved. |
| Assignment create/cancel/reassign | Domain service hooks exist for creation and reassignment; cancellation service exists. | Blocked: creation API absent; cancellation/reassignment return 503; authority unresolved. |
| Assignment expiry | Enum value and schema vocabulary exist. | Not implemented: no transition, timer, worker, or approved timeout policy. |
| Evidence upload/retrieval | Models and lifecycle coordination exist; integrity constraints are present. | Blocked: no configured provider/verifier; metadata/media routes and upload sessions unavailable. |
| Location create/verify/correct/read | Typed models and policy-gated domain service functions exist. | Blocked: role/scope policy unresolved; location API returns 503; conflict/external-source gaps remain. |
| AI_SERVICE intake | Separate machine actor/authentication adapter contract exists. | Blocked: authenticator is unconfigured under OAD-017; service intake fails closed. |
| Live dispatch/agency notification | No prototype support is intended. | Prohibited by prototype safety boundary. |

Implementation evidence is not stakeholder approval. The current fail-closed responses must remain until approval is recorded.

## Approval Gate

Before enabling candidate, incident, evidence, location, or assignment-management operations, record approvals for:

1. Candidate reviewer identity, candidate scope, review assignment, number of final reviewers, evidence checklist, rationale rule, and rejection/revision semantics.
2. Incident resolver/closer authority, no-assignment outcome, override scope, reopening/invalidity policy, and terminal assignment rule including `EXPIRED`.
3. Assignment creation, cancellation, reassignment, target eligibility, non-acknowledgement policy, and any simulated overdue indicator.
4. Evidence classification, role-specific metadata/media scope, provider/transfer/retrieval design, integrity/scanning criteria, retention, legal hold, deletion approver, and audit-reader scope.
5. Location claim owners/origins, precision/display scope, external-report provenance, competing claims, correction authority, and history retention.
6. AI machine-auth mechanism, credential lifecycle, replay/rate limits, narrowly scoped capabilities, source authorization, and safe failure behavior.

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

Tests should prove that: unauthorized roles cannot inspect candidate/evidence/location; active membership and assignment scope are enforced on each request; out-of-scope reads are concealed consistently; unresolved policy never grants access; concurrent candidate verification creates at most one incident; transaction failure commits neither decision nor incident; retries with matching commands are idempotent and mismatches conflict; assignment updates cannot change another target; notification/read state never acknowledges an assignment; `EXPIRED` is unusable until timeout policy is active; evidence is unavailable until validated and inaccessible after expiry; location source/uncertainty and correction history survive writes; audit events include actor/outcome without sensitive payload; and no prototype action sends a real notification/dispatch.

These are future acceptance criteria. No tests were run for this documentation-only task.

## Current Blockers and Dependencies

- OAD-012 blocks candidate queue/review/verification/rejection and, as referenced by the authorization contract, incident resolution/closure.
- OAD-013/OAD-018 block assignment creation, cancellation, and reassignment authority.
- OAD-002/OAD-014/OAD-016 block complete evidence storage/retrieval and lifecycle operation.
- OAD-001/OAD-020 block location access/display and authority.
- OAD-017 blocks AI_SERVICE intake because no authenticator is configured.
- OAD-021 blocks expiry behavior; the model enum alone does not provide a transition.
- Current requirements and OAD documents are still revised drafts; approval records are absent.

Until those blockers are resolved, Phase 5D remains partial and privileged workflows are not ready to enable.
