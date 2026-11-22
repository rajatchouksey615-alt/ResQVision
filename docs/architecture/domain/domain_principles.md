# Domain Principles

**Decision status:** Proposed governance baseline with project-owner-approved workflow and candidate-review policy slices dated 2026-11-19 and 2026-11-21; broader business policy and runtime permissions remain unapproved/unavailable.
**Basis:** Requirements and OAD documents are `REVISED_DRAFT`; implementation evidence does not confer approval.

This document converts the supplied domain principles into traceable domain and security invariants. `Documented` means present in the draft requirements/design. `Implemented` means code evidence exists. Neither label means a stakeholder approved the policy.

## Domain and Security Invariants

| ID | Principle | Rule to preserve | Repository evidence / status |
|---|---|---|---|
| DP-01 | Single source of truth | Django is authoritative for identities, authorization, candidate and incident state, assignments, and evidence access decisions. Clients and AI submit commands/observations; they do not write authoritative state directly. | SRS §6; `backend/api/v1`; proposed/documented and partly implemented. |
| DP-02 | Separate observation, candidate, incident | `DetectionEvent` is an AI observation; `AccidentCandidate` is a potential event under review; `AccidentIncident` is authoritative after human verification. The owner approved exactly one `OPEN` incident after `VERIFIED`, and none for `REJECTED`/`FURTHER_REVIEW`. Do not collapse the three records. | FR-004/005/018/019; separate Django models/FKs; OAD-015 policy slice approved 2026-11-21, intake remains open. |
| DP-03 | Human accountability | Only the specifically assigned and authorized human Police reviewer with active membership in the candidate's assigned Police organization may review it. AI detection never independently establishes an accident or records a decision. | `CandidateReview.reviewer`; OAD-005/012 policy slice approved 2026-11-21; assignment/org binding and runtime policy absent. |
| DP-04 | Least privilege | Grant only a specific action over a specific approved scope. `ADMIN`, `POLICE`, and `HOSPITAL` names alone do not imply global access. | Role matrix and API contract; no blanket Admin policy in selectors. |
| DP-05 | Organization isolation | Candidate review requires active membership in the Police organization to which the candidate is assigned and the assigned-candidate relationship. Police group membership alone grants no candidate access. A membership in one organization grants no access to another. | Owner-approved OAD-012 boundary; `OrganizationMembership` exists, but candidate organization/reviewer binding and policy do not. |
| DP-06 | Independent agency operations | Each Police/Hospital assignment owns its response state/history. An agency cannot mutate another assignment. Notification state is independent too. | OAD-018 proposed; `ResponseAssignment`, `Response`, history, and target-membership checks implemented. |
| DP-07 | Fail closed | Missing policy, untrusted actor, stale state, or ambiguous authority denies privileged work. Do not use UI hiding as a substitute. | `DenyByDefaultPolicy`; blocked API views; candidate/evidence/location/lifecycle routes return policy-unavailable errors. |
| DP-08 | Auditability | Candidate assignment, review, decisions, and incident creation must have traceable audit records, with safe attributable context. | Owner-approved 2026-11-21; `AuditEvent` covers candidate create/associate/start/verify/reject and verified incident, but not assignment or `FURTHER_REVIEW`; audit access/retention remain unresolved. |
| DP-09 | Transactional integrity | Current state, transition history, and successful audit commit together. Related records such as verified candidate and incident are atomic. | Candidate and incident services use `transaction.atomic`; database constraints backstop relationships. |
| DP-10 | Idempotent commands | Retrying an identical command yields the original result; reusing a command ID for a different action is a conflict. Unique constraints, not prechecks alone, protect races. | Candidate review, incident/assignment histories, response activities, and event identities have command/unique protections. |
| DP-11 | Evidence confidentiality | Evidence is private by default. Backend authorization controls metadata and media separately; a public object URL is not an authorization policy. | OAD-016 and NFR-006/022; metadata and upload-session models exist; no configured storage workflow. |
| DP-12 | Location provenance | Camera position, inferred accident location, reported location, and human-reviewed/corrected location are not interchangeable. Preserve source, time, uncertainty, and correction history where available. | OAD-020; `LocationRecord` distinguishes camera/accident claims; external-report source distinction remains absent. |
| DP-13 | No fabricated operational data | Unknown location, evidence, status, or response remains unknown/unavailable. Do not manufacture coordinates, precision, notification delivery, treatment, dispatch, or verification. | NFR-005/016/020/024; read-only mobile incident view and no live delivery route. |
| DP-14 | Prototype safety boundary | No real emergency dispatch, agency notification delivery, ambulance dispatch, or external emergency-service integration. Response and notification outcomes are simulated. | OAD-007 and NFR-020; draft constraint and implementation boundary. |

## Identity and Authority Boundaries

| Principal | Identity type | Proposed capability boundary | Current implementation evidence |
|---|---|---|---|
| ADMIN | Human Django user/group | Only explicit, audited administrative actions. No implicit global incident, evidence, location, or audit access. Reviewer/resolver/assignment powers need separate approval. | Incident visibility is membership/assignment-scoped; unapproved actions fail closed. |
| POLICE | Human Django user/group plus active Police membership | Candidate access is only for the specifically assigned and authorized reviewer, with active membership in the candidate's assigned Police organization. Assignment is made by an explicitly authorized authority within that organization. | Policy boundary approved 2026-11-21; assignment authority mechanism and candidate binding are unresolved; candidate routes remain blocked. |
| HOSPITAL | Human Django user/group plus active Hospital membership | View/update only its authorized Hospital-target assignment and minimum approved information. Readiness is not treatment. No candidate decision authority by default. | Activity kind is target-specific; candidate/evidence routes blocked. |
| AI_SERVICE | Separate machine actor | Only explicitly configured event intake and asset-specific evidence upload/completion. No human account, candidate decision, incident, assignment, notification, or general evidence-read authority. | `MachineActor` is separate; authenticator is unconfigured so event intake fails closed. |
| Source owner/operator | External governance actor | Owns permission for source use; not assumed to have an app role or login. | Source registration authority remains open under OAD-019. |

## Business Invariants

1. Allowed human Police candidate outcomes are `VERIFIED`, `REJECTED`, and `FURTHER_REVIEW`. Only `VERIFIED` atomically creates exactly one authoritative `OPEN` `AccidentIncident`; `REJECTED` and `FURTHER_REVIEW` create none, and further review preserves the candidate for subsequent review.
2. One DetectionEvent may be associated with at most one candidate in the current model. Similar-event grouping remains a separate decision; uncertain matches are not silently merged.
3. A verified candidate has at most one linked incident under the unique candidate relationship. Candidate final review is one-per-candidate in the current MVP model.
4. Police and Hospital assignment histories remain separate. Acknowledgement alone does not move the incident to `RESPONSE_ACTIVE`; the first assignment `IN_PROGRESS` transition does. Neither one agency's completion nor notification delivery closes an incident.
5. Evidence availability is a state of validated metadata/object integrity, not a claim of admissibility or operational truth.
6. Location precision reflects supplied accuracy. Decimal coordinate scale is storage precision and does not imply measurement accuracy.

## Security Invariants

- Every API read/write checks authenticated principal, current active account, role where required, object relationship, organization scope, and lifecycle preconditions.
- Out-of-scope incident/assignment reads are concealed by scoped querysets and return 404. Operations whose policy is not configured return 503 without checking resource existence. Keep these deterministic distinctions.
- Use command IDs and database uniqueness for consequential retries. Use a lock/state recheck for final review and lifecycle operations.
- Audit only allow-listed context. Never store tokens, passwords, raw media, signed URLs, storage credentials, unrestricted request bodies, or unnecessary personal/location data in audit/log records.
- Retention, legal hold, access review, and audit-reader authority must be approved before data collection or purge workflows are enabled.

## Action-to-Audit Matrix

| Action | Required attributable record | Safe context / sensitive-data boundary |
|---|---|---|
| Candidate assignment | Explicit assignment authority, candidate, relevant Police organization, assigned reviewer, action/time/outcome. | Use safe identifiers and allow-listed fields; no global Admin grant or audit-reader access is implied. |
| Candidate review start | Actor, candidate, prior/resulting state, UTC time, outcome, command/request ID. | Do not copy review notes or evidence bytes into audit context. |
| Candidate `VERIFIED` / `REJECTED` / `FURTHER_REVIEW` | Reviewer, candidate, outcome, timestamp, command ID; incident UUID only for verification. | Keep any rationale in the protected domain record; audit context uses allow-listed identifiers/status only. |
| Incident resolve/close | Actor, incident, prior/resulting state, reason in the protected history, time, outcome, command ID. | Never include unrelated agency notes or raw evidence in audit context. |
| Assignment create/acknowledge/progress/complete/unable/cancel/reassign/expire | Actor, assignment, target organization, incident, transition, time, outcome, command ID, reason where required. | Keep Police/Hospital histories separate; no treatment or dispatch claim in free-text audit fields. |
| Evidence upload/validation/access/association/expiry/deletion | Actor/service, asset and target IDs, operation, validation/access outcome, time, request/command ID, safe failure code. | Never log media, original unrestricted request bodies, public/signed URLs, credentials, or raw provider payloads. |
| Location create/verify/correct | Actor/service, location and subject IDs, source/event IDs, action, outcome, time; corrections include reason and before/after values in the protected correction-history record. | Treat coordinates and accuracy as sensitive; keep full precision out of general operational logs. |
| Authorization denial or invalid transition | Actor/principal kind where known, operation, resource type/UUID where safe, outcome, request ID, stable reason code. | For unresolved-policy endpoints, return policy-unavailable without resource lookup; do not leak existence. |
| AI event intake and retry | Machine principal, source/event identity, accepted/duplicate/denied result, timestamp, request ID. | No machine secret or raw video/payload in audit context. |

The matrix describes the minimum audit intent. Audit access, retention, and any regulatory retention obligations remain unapproved decisions.

## Proposed Interpretation Rule

Where a requirement or OAD says “must” but its parent document remains a draft, treat it as the current design baseline and implementation target, not as approved organizational policy. Where runtime behavior exists without supporting approval, preserve it only as a factual implementation description. Unresolved permissions remain denied by default.
