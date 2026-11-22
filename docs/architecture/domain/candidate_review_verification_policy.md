# Candidate Review and Verification Policy

**Decision status:** The project owner approved the policy principles below on 2026-11-21. Runtime authorization and the unimplemented `FURTHER_REVIEW` outcome remain blocked pending technical and authority prerequisites.
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

These decisions do not enable a runtime permission, candidate API, AI intake path, or new role. They do not approve particular candidate fields, evidence/media/location access, review criteria, or an assignment technology.

## Authorization and Assignment Matrix

| Action | Approved authority and scope | Current implementation evidence | Readiness |
|---|---|---|---|
| Assign a candidate to a Police organization/reviewer | An explicitly authorized authority acting within the relevant Police organization. | `AccidentCandidate` has no Police organization or assigned-reviewer field; no assignment service or API exists. | Policy boundary approved; authority mechanism and runtime blocked under OAD-012. |
| List candidate queue | Specifically assigned, authorized human Police reviewers with active membership in the relevant organization; only their assigned candidates. | `list_reviewable_candidates` invokes `candidate.read_queue`, but no policy is configured and the selector has no organization/assignee scope. Candidate API returns policy-unavailable. | Policy approved; blocked in runtime. |
| Read candidate detail | Same reviewer, active organization, and assigned-candidate scope. Returned fields still need field-level approval. | `get_candidate` invokes `candidate.read`; candidate detail API is blocked. No candidate access policy or Police assignment relation exists. | Policy approved; fields and runtime blocked. |
| Start or conduct review | Specifically assigned and authorized human Police reviewer, with active membership in the candidate's assigned Police organization. | `begin_candidate_review` requires a human actor and injected policy, locks the candidate, moves `RECEIVED` to `UNDER_REVIEW`, and audits. It does not check assignment or Police organization. API is blocked. | Policy approved; assignment binding and runtime blocked. |
| Record `VERIFIED` | Same assigned and authorized human reviewer. Exactly one authoritative `OPEN` incident is created in the same transaction. | `verify_candidate` requires a human actor and injected policy; the transaction writes a final review, candidate status, incident, initial history, and audit. Unique constraints, row locking, and command IDs protect duplicate/concurrent finalization. API is blocked. | Outcome and consistency approved; authorization and API blocked. Existing service is reusable. |
| Record `REJECTED` | Same assigned and authorized human reviewer; no incident is created. | `reject_candidate` writes a final review/status and audit, with no incident. Current implementation requires nonblank rejection rationale; that requirement was not part of this owner approval. API is blocked. | Outcome approved; authorization/API blocked. Preserve current runtime validation unless separately decided. |
| Record `FURTHER_REVIEW` | Same assigned and authorized human Police reviewer; no incident; candidate remains available for subsequent review. | Neither `ReviewDecision` nor `CandidateStatus` includes this outcome. No non-final decision record/action exists. `begin_candidate_review` rejects an already `UNDER_REVIEW` candidate, so the current path cannot record the outcome and proceed to a subsequent review. | Policy approved; implementation blocked. Add no new business meaning beyond the approved outcome. |
| Record candidate assignment/review/decision/incident audit | Traceable records for each named operation; audit content remains safe and attributable. | Audit exists for candidate creation, association, review start, verify, and reject, and the verified incident ID is included in the success audit context. Candidate assignment and `FURTHER_REVIEW` have no record/action. | Partially implemented; assignment and `FURTHER_REVIEW` audit need implementation. |
| AI candidate decision | None. AI detection never verifies an accident or records any of the three human outcomes. | Final decision service requires a human actor. Machine authentication is unconfigured and candidate APIs are blocked. | Prohibited for AI; no final decision permission. |

No `POLICE` group-wide queue, cross-organization access, global Admin bypass, or newly named human role is approved. A candidate must be scoped to a Police organization and assigned reviewer before review access can be evaluated; those relationships do not exist in the current model. Do not substitute incident-response assignment scope for candidate assignment.

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

Current audit events cover candidate creation, event association, review start, verified/rejected decisions, and successful incident creation in the verified transaction. There is no candidate-assignment operation or `FURTHER_REVIEW` audit record. Audit reader scope, retention, and integrity governance remain open. Audit payloads must continue to use safe allow-listed fields; they must not include evidence bytes, secrets, or unrestricted rationale/media.

## Required Gates Before Runtime Enablement

1. Identify which existing backend permission/mechanism authorizes candidate assignment within the relevant Police organization. Do not enable global Admin authority or introduce a new role by default.
2. Establish the candidate-to-Police-organization and candidate-to-assigned-reviewer scope in an approved way, with active membership rechecked for each review request.
3. Approve the DetectionEvent intake/materialization path, AI machine authentication, source authorization, and duplicate-submission controls before enabling candidate intake.
4. Implement the already approved `FURTHER_REVIEW` outcome so it creates no incident and preserves the candidate for a subsequent review, with a traceable audit record.
5. Configure and verify server-side action/resource policy for queue, detail, review, and each decision. Keep candidate endpoints fail-closed until these conditions hold.
6. Preserve the existing atomic verified-incident transaction and add acceptance coverage for organization isolation, assigned-candidate scope, concurrent/duplicate verification, rejection, and subsequent review.

These gates do not require selecting a checklist, threshold, rationale policy, review-count rule, or new role unless a later owner decision explicitly does so.
