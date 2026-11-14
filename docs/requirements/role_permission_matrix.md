# Role-Permission Matrix

**Status:** REVISED_DRAFT — pending team approval. Backend enforcement is required; no role grants real emergency-service access.

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
| Submit DetectionEvent | No | No | No | Yes, authenticated |
| Retry same DetectionEvent identity | No | No | No | Yes, idempotent only |
| Associate events to AccidentCandidate | Backend policy only | No | No | No |
| View candidate queue | Scoped administrative review | No by default | No by default | Own submission outcome only |
| Verify/reject AccidentCandidate | Designated reviewer; ADMIN proposed, authority TBD | No unless separately approved reviewer | No unless separately approved reviewer | No |
| Create AccidentIncident | Backend only after authorized human verification | No | No | No |
| View incident summary | Need-to-know scope | Assigned Police target only | Assigned Hospital target only; minimum data | No |
| View EvidenceAsset metadata | Need-to-know; sensitive access audited | Scoped to Police assignment | Scoped and minimized to Hospital assignment | Own submitted assets only |
| Upload evidence bytes | No direct broad storage access | No | No | Only backend-authorized object, short-lived/scoped |
| Retrieve evidence bytes | Backend-authorized scoped access | Scoped; policy TBD | Scoped and minimized; policy TBD | No general read access |
| Create ResponseAssignment | Proposed Admin/approved assignment mechanism; policy TBD | No | No | No |
| Acknowledge own assignment | No | Scoped to assigned Police target | Scoped to assigned Hospital target | No |
| Record Response/progress/completion | Administrative oversight only; TBD | Own assignment only | Own assignment only; readiness only | No |
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

## Approval Decisions

- Final candidate reviewer/verification authority and whether a separate human reviewer role is needed.
- Who may register VideoSources and what evidence of owner permission is required.
- Police/Hospital assignment scope and target eligibility.
- Assignment creation, cancellation, reassignment, and timeout authority.
- Incident resolution, closure, reopening, override, and handling of unfinished assignments.
- Evidence fields/media available to each human role and audit-history visibility.
