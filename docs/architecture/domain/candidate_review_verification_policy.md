# Candidate Review and Verification Policy

**Decision status:** The project owner approved the policy principles below on 2026-11-21. As of 2026-11-22, assigned candidate reads, review start, `VERIFIED`, and `REJECTED` are implemented in the backend and Police Flutter app. `FURTHER_REVIEW` remains unavailable until its persistence and subsequent-review lifecycle are approved and implemented. Production AI ingestion, evidence, and location access remain fail-closed.
**Related existing decisions:** OAD-005, OAD-012, OAD-015. Candidate reviewer assignment is governed by OAD-012; OAD-013 concerns incident-response assignment and is not a candidate-review authority.
**Related requirements:** FR-004, FR-005, FR-017, FR-018, FR-019; NFR-002, NFR-008, NFR-009, NFR-019.

## Owner-Approved Policy

The following are explicit project-owner decisions, not recommendations:

1. **Candidate access:** Only the specifically assigned and authorized human Police reviewer may review a candidate. The reviewer must have an active Police organization membership in the organization to which the candidate is assigned. Access is limited to that assigned candidate and active organization scope. Membership in the general `POLICE` group alone does not grant access.
2. **Candidate assignment:** Assignment must be performed by an explicitly authorized authority within the relevant Police organization. This does not grant unrestricted `ADMIN` access and does not establish a new human role. Which existing backend permission or mechanism supplies this authority remains unresolved.
3. **Decision authority:** Only an authorized human Police reviewer may record a candidate decision. AI detection is an observation and must never independently establish an accident.
4. **Allowed outcomes:** `VERIFIED`, `REJECTED`, and `FURTHER_REVIEW`.
   - `VERIFIED` creates exactly one authoritative `OPEN` `AccidentIncident`.
   - `REJECTED` creates no `AccidentIncident`.
   - `FURTHER_REVIEW` creates no `AccidentIncident` and preserves the candidate for subsequent review.
5. **Consistency:** Recording `VERIFIED` and creating its incident are atomic and safe against duplicate or concurrent requests.
6. **Auditability:** Candidate assignment, review, decisions, and incident creation have traceable audit records.

The 2026-11-21 policy approval established the authority boundary; the assigned-review runtime was implemented on 2026-11-22. The approval did not enable AI intake or a new role, and does not approve evidence/media/location access or additional review criteria.

## Authorization and Assignment Matrix

| Action | Approved authority and scope | Current implementation evidence | Readiness |
|---|---|---|---|
| Assign a candidate to a Police organization/reviewer | An explicitly authorized authority acting within the relevant Police organization. | `AccidentCandidate` is bound to a Police organization. `CandidateReviewerAssignment` stores one append-only assignment. The service and API require the existing `ADMIN` group plus active membership in that organization and an active same-organization Police reviewer. | Implemented; assignment is one-time and cannot be reassigned. |
| List candidate queue | Specifically assigned, authorized human Police reviewers with active membership in the relevant organization; only their assigned candidates. | The candidate selector scopes by reviewer, active account, active Police organization, matching candidate binding, and active Police membership before pagination. | Implemented; out-of-scope candidates are not listed. |
| Read candidate detail | Same reviewer, active organization, and assigned-candidate scope. | Candidate detail uses the same scoped selector and returns only the existing summary fields: identifiers, status, and timestamps. Evidence media and location are not exposed. | Implemented within the existing summary contract. |
| Start review | Specifically assigned and authorized human Police reviewer, with active membership in the candidate's assigned Police organization. | `begin_candidate_review` locks the active reviewer and candidate, checks the assigned-reviewer policy and provenance, moves `RECEIVED` to `UNDER_REVIEW`, and audits. | Implemented through the authenticated review endpoint. |
| Record `VERIFIED` | Same assigned and authorized human reviewer. Exactly one authoritative `OPEN` incident is created in the same transaction. | `verify_candidate` locks reviewer and candidate, checks the same policy, and writes the final review, candidate status, incident, initial history, and audit atomically. Unique constraints and command IDs protect duplicate/concurrent finalization. | Implemented through the authenticated verification endpoint. |
| Record `REJECTED` | Same assigned and authorized human reviewer; no incident is created. | `reject_candidate` writes the final review/status and audit without an incident. The existing nonblank rationale requirement is preserved. | Implemented through the authenticated rejection endpoint. |
| Record `FURTHER_REVIEW` | Policy notes an inconclusive outcome, but detailed persistence and subsequent-review lifecycle remain unresolved. | No runtime operation is exposed. The existing model stores only final decisions and does not support a later review cycle. | Unavailable until the detailed policy is approved. |
| Record candidate assignment/review/decision/incident audit | Traceable records for each named operation; audit content remains safe and attributable. | Assignment, review start, verification, rejection, and verified incident creation have attributable audit events. Decision rationale is not copied to audit metadata. | Implemented for available operations. |
| AI candidate decision | None. AI detection never verifies or rejects accidents. | Final decision services require a human actor. Production machine authentication and event ingestion remain fail-closed. | Prohibited for AI. |

No `POLICE` group-wide queue, cross-organization access, global Admin bypass, or newly named human role is approved. A candidate must be bound to a Police organization and assigned to one reviewer before review access can be evaluated. Do not substitute incident-response assignment scope for candidate assignment.

## Decision Lifecycle and Runtime Compatibility

The approved decision semantics are:

| Outcome | Authoritative incident | Candidate handling |
|---|---|---|
| `VERIFIED` | Exactly one linked incident with status `OPEN`, committed atomically with the decision. | Verified candidate. |
| `REJECTED` | None. | Rejected candidate. |
| `FURTHER_REVIEW` | None. | Preserve the candidate so it can be reviewed subsequently. |

The current model stores only final `VERIFIED` and `REJECTED` `CandidateReview` decisions. It supports `RECEIVED`, `UNDER_REVIEW`, `VERIFIED`, and `REJECTED` candidate statuses, with one final review and at most one incident per candidate. The verified service path already meets the approved atomic `OPEN` incident invariant. The rejection path already creates no incident. `FURTHER_REVIEW` is not supported and the current begin-review command does not let an already `UNDER_REVIEW` candidate proceed to another review. This is a material implementation gap, not an ambiguity in the approved outcome.

The owner approval does not specify which candidate fields or media may be viewed, verification thresholds/checklists, rationale requirements, review-count limits, or how assignment changes after `FURTHER_REVIEW`. Do not infer those business rules from code. The current service requires a rejection rationale and allows an empty verification rationale; record this as existing runtime behavior, not as a new owner-approved rule. Any change to that behavior requires its own decision.

## Intake, Provenance, and Audit Boundaries

`DetectionEvent` is an observation, not a verified accident. The existing service can create a candidate from one explicitly selected event; event creation does not automatically materialize a candidate. Similar-event grouping and candidate merge are not implemented or approved. `(video_source, external_event_id)` uniqueness and one-event-to-one-candidate association protect specific duplicate paths, but do not settle candidate intake authorization or broader duplicate-submission policy.

The owner has not decided how `DetectionEvent` becomes an `AccidentCandidate`, what authentication the AI service uses to submit events, or how intake is protected from unauthorized or duplicate submissions. OAD-015 event/grouping scope, OAD-017 machine authentication, and OAD-019 source authority remain open. Do not expose machine or human candidate creation by inferring permission from the approved Police review policy.

Current audit events cover candidate assignment, candidate review start, verified/rejected decisions, and successful incident creation in the verified transaction. There is no `FURTHER_REVIEW` audit record because no runtime operation exists. Audit reader scope, retention, and integrity governance remain open. Audit payloads use safe allow-listed fields and do not include evidence bytes, secrets, or decision rationale.

## Remaining Runtime Boundaries

1. Keep `FURTHER_REVIEW` unavailable until its persistence and subsequent-review lifecycle receive detailed approval.
2. Keep production AI ingestion fail-closed until machine authentication, source authority, and event-to-candidate intake are approved and configured.
3. Keep evidence and location endpoints unavailable; the Police candidate detail remains limited to the existing summary contract.
4. Keep Hospital notification, response assignment, dispatch, and external emergency-service integration outside candidate review.
5. Preserve the atomic verified-incident transaction and regression coverage for organization isolation, assigned-candidate scope, concurrent/duplicate decisions, rejection, and audit.

These gates do not require selecting a checklist, threshold, rationale policy, review-count rule, or new role unless a later owner decision explicitly does so.
