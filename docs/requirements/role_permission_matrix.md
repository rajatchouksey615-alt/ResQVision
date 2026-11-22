# Role-Permission Matrix

**Status:** REVISED_DRAFT — pending team approval. The project owner approved a Police-first simulated response workflow on 2026-11-19 and candidate assignment/access/outcome policy slices on 2026-11-21. These are policy boundaries, not runtime grants. The candidate assignment authority mechanism remains unresolved. Backend enforcement is required; no role grants real emergency-service access.

## Principals

- **ADMIN, POLICE, HOSPITAL** are human application roles authenticated through the human identity flow.
- **AI_SERVICE** is a separate machine identity, not a human role or a Flutter login role. It has narrowly scoped event and evidence-transfer capabilities.
- **Source owner/operator** is an external data-governance actor, not an assumed application role. Source registration authority is pending approval.

Legend: **Yes (proposed)** = allowed under a draft baseline; **Scoped** = only on the principal's authorized target/objects; **TBD** = requires team/institution policy approval; **No** = prohibited.

| Resource/action | ADMIN | POLICE | HOSPITAL | AI_SERVICE |
|---|---|---|---|---|
| Authenticate to own human account | Yes (proposed) | Yes (proposed) | Yes (proposed) | Uses separate machine authentication |
| Create/disable users and assign ADMIN/POLICE/HOSPITAL roles | Yes (proposed) | No | No | No |
| Register/authorize/suspend VideoSource | Proposed operator; owner approval required | No | No | No |
| Submit DetectionEvent | No | No | No | Blocked until approved machine authentication/source contract; no mechanism enabled |
| Retry same DetectionEvent identity | No | No | No | Yes, idempotent only |
| Associate events to AccidentCandidate | Backend policy only | No | No | No |
| Assign candidate to Police organization/reviewer | No authority from ADMIN role alone; may act only if separately authorized within the relevant Police organization; mechanism TBD | Explicitly authorized authority within the relevant Police organization; existing permission/mechanism unresolved | No | No |
| View candidate queue/detail | No authority from ADMIN role alone; only a person separately assigned and authorized as Police reviewer with active membership in the candidate's assigned Police organization | Specifically assigned and authorized human Police reviewer only, with active membership in the candidate's assigned Police organization; assigned candidate only | No | No candidate access/decision |
| Record `VERIFIED`, `REJECTED`, or `FURTHER_REVIEW` | No authority from ADMIN role alone; only a person separately assigned and authorized as Police reviewer with active membership in the candidate's assigned Police organization | Specifically assigned and authorized human Police reviewer; `VERIFIED` creates exactly one atomic `OPEN` incident, other outcomes create none; `FURTHER_REVIEW` preserves candidate for subsequent review | No candidate decision authority | No; AI never independently establishes an accident |
| Create AccidentIncident | Backend only after authorized human `VERIFIED`; exactly one linked `OPEN` incident | No direct creation | No | No |
| Audit candidate assignment/review/decisions/incident creation | No audit-reader access implied | No audit-reader access implied | No audit-reader access implied | No |
| View incident summary | Need-to-know scope | Assigned Police target only | Assigned Hospital target only; minimum data | No |
| View EvidenceAsset metadata | Need-to-know; sensitive access audited | Scoped to Police assignment | Scoped and minimized to Hospital assignment | Own submitted assets only |
| Upload evidence bytes | No direct broad storage access | No | No | Only backend-authorized object, short-lived/scoped |
| Retrieve evidence bytes | Backend-authorized scoped access | Scoped; policy TBD | Scoped and minimized; policy TBD | No general read access |
| Create ResponseAssignment | Proposed Admin/approved assignment mechanism; policy TBD | No | No | No |
| Acknowledge own assignment | No | Scoped to assigned Police target | Scoped to assigned Hospital target | No |
| Record Response/progress/completion | Administrative oversight only; TBD | Own Police assignment only | Own designated Hospital request/assignment only; acknowledgement, availability/inability, and simulated dispatch/status are separate; exact statuses TBD | No |
| Mark UNABLE_TO_RESPOND | No | Own assignment with reason | Own assignment with reason | No |
| Cancel or reassign assignment | Proposed authorized Admin; approval TBD | No | No | No |
| Cause assignment EXPIRED | Backend only if timeout policy approved | No | No | No |
| Resolve/close/reopen AccidentIncident | Designated authorized reviewer; exact authority TBD | No by default | No | No |
| Read Notification state | Authorized administrative scope | Own target notification | Own target notification | No |
| Mark Notification READ | No | Own notification only | Own notification only | No |
| View incident/assignment history | Authorized admin/auditor scope TBD | Scoped history | Scoped history | Own event submission outcome only |
| View aggregate reports | Proposed Admin; privacy filters required | No by default | No by default | No |
| Trigger real emergency notification/dispatch | No in prototype | No in prototype | No in prototype | No |

## Required Authorization Behavior

1. Backend checks identity, role/principal type, object relationship, assignment target, requested operation, and current lifecycle state on every protected request.
2. Route hiding in Flutter is supplementary; it is never the authorization decision.
3. A role alone does not grant all incident/evidence access. Police and Hospital see only their assigned target and minimum authorized data.
4. AI_SERVICE may submit events and request/upload/report completion only for its own server-issued EvidenceAsset authorization. It cannot browse media, verify candidates, create incidents, create assignments, or update any response state.
5. An EvidenceAsset is retrievable only when AVAILABLE and after object-level authorization. The object-store provider does not make access decisions.
6. Notification states do not substitute for assignment acknowledgement. An assignment acknowledgement does not change another assignment or incident state.
7. Denials do not reveal whether out-of-scope incidents or evidence exist. Sensitive access attempts and successful reads are audited.
8. Admin remains subject to least privilege; administrative status does not imply unrestricted evidence or audit access.

## Project-Owner-Approved Workflow Scope (2026-11-19)

The project owner approved on 2026-11-19 that a specifically authorized human Police reviewer makes the candidate decision before a Hospital response request is generated. After a verified candidate creates one linked `OPEN` incident, the backend creates a request for the designated Hospital. An authorized Hospital user records acknowledgement and availability/inability, followed by a distinct simulated ambulance-dispatch decision and subsequent simulated response status. Police and Hospital scopes remain independent; all such outcomes are simulated and no external emergency service is contacted.

This approves the workflow role and ordering only. It does not authorize all members of `POLICE` or `HOSPITAL`, define which person or organization is selected, specify the review information/criteria, grant Admin global access, define response status enums, or enable runtime APIs. See the [Accident Verification and Emergency Response Governance Workflow](../architecture/domain/accident_verification_emergency_response_workflow.md). The existing OAD status rows remain unchanged until separately recorded in the decision process.

## Approval Decisions

- Specific Police reviewer identities/groups, candidate/source/jurisdiction scope, review assignment, decision count, checklist, rationale, and permitted information.
- Who may register VideoSources and what evidence of owner permission is required.
- Police/Hospital assignment scope and target eligibility.
- Hospital target selection/routing, request creation/retry semantics, assignment cancellation/reassignment, and timeout authority.
- Hospital availability, simulated ambulance-dispatch decision, and subsequent response status vocabulary/transitions and authorized readers.
- Incident resolution, closure, reopening, override, and handling of unfinished assignments.
- Evidence fields/media available to each human role and audit-history visibility.

## Subsequent Project-Owner Candidate Review Policy Approval (2026-11-21)

This later approval settles the candidate policy boundaries while preserving the separate 2026-11-19 workflow record above:

- Only the specifically assigned and authorized human Police reviewer with active membership in the candidate's assigned Police organization may access/review that candidate.
- Candidate assignment must be performed by an explicitly authorized authority within the relevant Police organization. The existing backend permission/mechanism remains unresolved; no global Admin bypass or new human role is approved.
- Only an authorized human Police reviewer records `VERIFIED`, `REJECTED`, or `FURTHER_REVIEW`. Only `VERIFIED` creates exactly one atomic linked `OPEN` incident; other outcomes create none, and further review preserves the candidate for subsequent review.
- Candidate assignment, review, decisions, and incident creation must have traceable audit records.

This approval does not resolve event-to-candidate materialization, AI machine authentication, duplicate-submission controls, candidate organization/reviewer data binding, or the implementation gaps for `FURTHER_REVIEW`. It does not change the matrix status from `REVISED_DRAFT` or grant runtime access.
