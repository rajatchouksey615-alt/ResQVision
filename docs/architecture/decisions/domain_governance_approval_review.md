# ResQVision Domain Governance Approval Review

**Review date:** 2026-11-19

**Original repository baseline:** `main`, `3c26c96541b9b97ead4b70608e580e28dd52cd58` (`docs(architecture): organize governance policies by domain`)

**Current update baseline:** `main`, `879438ff91c70461663b7ffa4c5bb4721ec3ce8f` (`docs(architecture): add domain governance approval review`)

**Review status:** Original review was recommendations only. A scoped project-owner-approved workflow decision supplied on 2026-11-19 is recorded below; no OAD status entry is changed.

**Purpose:** Close the policy questions that must be answered before privileged incident-management operations are enabled.

## Executive Summary

The repository has a coherent proposed domain architecture: Django REST Framework owns authoritative business state and authorization; `DetectionEvent`, `AccidentCandidate`, and `AccidentIncident` are separate; Police and Hospital assignments have separate scope and histories; and the academic prototype does not dispatch responders. The code and documentation also describe several useful controls, including transactionally creating an incident after candidate verification, scoped organization reads, idempotent commands, and fail-closed routes.

The governance is **not closed**. The architecture and requirements remain `REVISED_DRAFT`; the OAD register has no fully approved entries; and `docs/decisions/README.md` still says that no ADR has been approved. Since the original review, the project owner explicitly approved the workflow role/order of Police-first candidate verification followed by a simulated Hospital request/response. This approves neither a broad Police group grant nor the detailed identities, scopes, routing, response states, evidence/location access, incident resolver/closer, or AI machine-auth policy. Runtime behavior remains blocked where those details are unresolved.

Privileged implementation should not begin until the owner records the remaining action authority, lifecycle, source, retention, evidence, location, Hospital routing, and response-status decisions. Keep blocked operations fail closed. Separately, ratify or reconsider the limited incident reads and target-assignment commands already enabled; implementation and draft requirements do not establish that their scope was approved.

The recommended first implementation slice, after the remaining decisions, is a controlled synthetic/demo event intake, scoped Police candidate decision, atomic creation of one `OPEN` incident, and idempotent post-commit request for the designated Hospital. Then add Hospital acknowledgement/availability and distinct simulated ambulance-dispatch/status records. Do not add real external delivery. Evidence and location remain separately gated. No real police, hospital, ambulance, or other emergency dispatch is in scope.

## Subsequent Project-Owner Workflow Approval (2026-11-19)

The project owner approved the workflow stated in the task supplied for this update. The detailed flow, failure handling, open decisions, acceptance criteria, and proposed Phase 5E allocation are in the [Accident Verification and Emergency Response Governance Workflow](../domain/accident_verification_emergency_response_workflow.md).

Approved scope: an appropriately authorized human Police reviewer decides before any Hospital request; AI does not verify; successful verification atomically creates exactly one linked `OPEN` incident; rejected/inconclusive candidates create neither incident nor Hospital request; the backend then creates an incident-linked request for a designated Hospital; an authorized Hospital user records acknowledgement and availability/inability; Hospital records a separate simulated ambulance-dispatch decision and subsequent simulated response status; Police and Hospital access/history remain independent and auditable; all activity is simulated and no real emergency service is contacted.

Still pending: the Police reviewer’s identity and candidate scope, permitted review data and criteria, Hospital target/routing and request contract, response status vocabulary/transitions, field-level tracking permissions, evidence/location policies, source consent and machine authentication, retention/audit governance, and incident resolver/closer/timeout policy. This task-level approval does not itself create a runtime grant or an approved ADR.

## Current Governance Status

| Area | Repository status and evidence | Closure implication |
|---|---|---|
| Architecture baseline | `docs/architecture/README.md` and its linked architecture documents are `REVISED_DRAFT — pending team approval`. | Treat requirements and diagrams as design baselines, not approved organizational policy. |
| ADR approval | [`docs/decisions/README.md`](../../decisions/README.md) states that no ADRs have been approved. | There is no approved ADR that settles the reviewed authority questions. |
| OAD register | [`open_architecture_decisions.md`](../open_architecture_decisions.md) marks OAD-001–014 `TBD`; OAD-015–021 are `Proposed`, `TBD`, or proposed with a pending dependency/approval. Owner labels are placeholders. | Preserve all identifiers, wording history, and statuses; record any later acceptance as a dated OAD amendment or ADR. |
| Domain policies | Domain principles, candidate review, incident lifecycle, evidence, location, authorization matrix, decision register, and readiness documents all identify recommendations or unresolved authority. | None of these policies grants a runtime permission. |
| Runtime evidence | The readiness and authorization documents describe selected scoped incident/assignment reads and agency assignment updates as available; candidate, evidence, location, incident resolve/close, and assignment create/cancel/reassign paths are blocked or unavailable. AI intake fails closed while machine authentication is unconfigured. | Runtime availability is a fact to review, not approval. Ratify each already-enabled operation and continue to deny blocked actions until approved. |
| Prototype safety | OAD-007 records “Simulated only for prototype; later choice TBD”; NFR-020 prohibits real dispatch. The user’s review constraints also explicitly prohibit real emergency dispatch. | Keep all delivery and response outcomes simulated; no external emergency integration may be enabled by this review. |
| Git and source validation | Review began on `main` at the commit above with a clean worktree. The requested report path was absent. All local Markdown links in `docs/architecture/**` and the ADR index resolved; OAD-001–021 were present in the register. | This report is the only requested change. No application tests were run for this documentation-only review. |

The files referenced by the architecture README were followed, including the architecture overview, system and component architecture, trust boundaries, data flow, technology decisions, OAD register, and domain governance overview. The governance audit also covered the required domain policies, authorization matrix, implementation readiness, decision register, requirements, incident response workflow, API authorization contract, transaction design, and retention design.

## Approved Decisions

At the original audit baseline, no project or stakeholder-approved domain decision was recorded in the repository. The ADR index still has no approved ADR, and the OAD statuses remain as recorded. For this update, the project owner has explicitly approved the limited workflow scope in “Subsequent Project-Owner Workflow Approval” above. It is recorded as an owner-approved workflow decision, not as a new runtime grant or a blanket approval of the related OADs.

The following are documented constraints and current implementation facts to preserve during this review; they are not evidence of a prior project-owner approval:

- The review is governed by the request’s constraints: Django REST Framework is authoritative; `ADMIN`, `POLICE`, and `HOSPITAL` are separate human roles; `AI_SERVICE` is a separate machine identity; the three event/candidate/incident entities remain distinct; Police and Hospital scope remains independent; Admin has no assumed global access; and the prototype does not perform real emergency dispatch.
- The owner-approved Police-first workflow now settles the human reviewer role class and step ordering, the successful verification-to-incident outcome, the post-verification Hospital request, and the distinction between Hospital acknowledgement and simulated dispatch/status. It does not approve detailed reviewer or Hospital grants.
- The repository’s related DP, FR, NFR, OAD, and authorization documents remain drafts or proposals except for this explicitly recorded workflow slice; current implementation is still not policy approval.
- Current code facts include scoped reads and assignment commands, policy-blocked APIs, domain services and database constraints, and an unconfigured AI authenticator. These are not approvals for the corresponding policy.

## Unresolved Decisions

The status column preserves the current OAD entries. The third column distinguishes the scope the project owner approved in this update from remaining decisions and recommendations; no OAD status has been changed.

| OAD | Existing recorded status | Unresolved question and recommended default for this prototype | Implementation impact / approving roles |
|---|---|---|---|
| OAD-001 | `TBD` | Defer map provider. Keep coordinates hidden unless role, purpose, claim type, and precision are approved; a textual, explicitly labeled summary may be sufficient later. | Blocks map/location display. Project team and privacy/data-governance approver. |
| OAD-002 | `TBD` | Defer provider choice until evidence is needed. Any chosen store must be private, server-addressed, object-scoped, and reconcilable; use synthetic data only in a controlled demo meanwhile. | Blocks evidence upload/retrieval and deletion integration. Backend/security and data-governance owners. |
| OAD-003 | `TBD` | Select a reproducible detector only after an approved dataset and evaluation protocol exist. Do not claim accuracy or use model confidence as a decision threshold. | Blocks claims about model quality and evaluated intake. Project team and AI evaluation owner. |
| OAD-004 | `TBD` | Use the simplest reproducible temporal association suitable for the demo, or defer tracking; do not add complexity without evaluation evidence. | Affects model pipeline, event provenance, and evaluation. Project team and AI evaluation owner. |
| OAD-005 | `TBD` | AI output is evidence only. A human makes the final candidate decision; approve the model/method and thresholds separately from reviewer authority. | Blocks decision criteria and evaluation claims. Project team and AI evaluation owner. |
| OAD-006 | `TBD` | Start with a controlled file or synthetic fixture whose processing rights are documented; defer live streams/camera integration. | Blocks source ingestion beyond approved demo inputs. Source owner, project team, and security/data-governance owners. |
| OAD-007 | `Simulated only for prototype; later choice TBD` | The owner explicitly confirmed simulation for notifications, acknowledgements, dispatch decisions, and response outcomes; do not add live delivery in the academic prototype. | No real dispatch path may be enabled. This approved no-contact boundary does not select a later provider. |
| OAD-008 | `TBD` | For an approved prototype intake, prefer a small authenticated request/response contract with stable event IDs and safe retry semantics; defer a broker unless workload or reliability needs justify it. | AI/backend contract and idempotency need agreement. Backend/security and AI integration owners. |
| OAD-009 | `TBD` | Use local or institution-controlled demonstration infrastructure with synthetic/approved data; defer public deployment and production claims. | Blocks retained-data deployment until privacy, backup, and recovery controls are approved. Project team, privacy, and security owners. |
| OAD-010 | `TBD` | Keep the existing simple Flutter approach until a real approved workflow requires additional state management. | Not a domain-policy blocker; avoid adding client complexity before API contracts stabilize. Project team. |
| OAD-011 | `TBD` | Keep background work manual or minimal for the prototype. Do not add timeout, retention-purge, or external-delivery workers before their policies are approved. | Blocks automation with consequential lifecycle effects. Project team and operations/security owners. |
| OAD-012 | `TBD` | **Approved scope:** Police-first review by an appropriately authorized human Police reviewer. **Still pending:** identity/group, source/jurisdiction scope, queue/assignment, permitted fields, checklist, rationale, decision count, and conflict handling. Do not grant authority to every Police user. | Candidate routes remain blocked until the approved role is translated into explicit identities, scope, and policy. Project team/security and Police domain representative. |
| OAD-013 | `TBD` | **Approved scope:** After verified incident creation, the system creates a request for the designated Hospital. **Still pending:** who designates the target, eligibility/routing, request-to-assignment mapping, retries, and replacement. Do not assume all Admins may assign. | Request-creation route remains blocked until target and actor contracts are defined. Project team, backend/security, and Hospital representative. |
| OAD-014 | `TBD` | Do not invent retention periods. Approve purpose-specific durations, legal holds, backups, rejected-candidate evidence, evaluation copies, and deletion authority before collecting real data or enabling purge. | Blocks real-data ingestion and automated retention/deletion. Source owners and institutional privacy/data-governance approver. |
| OAD-015 | `Proposed; team approval required` | **Approved scope:** Keep `DetectionEvent`, `AccidentCandidate`, and `AccidentIncident` distinct; only successful authorized Police verification creates one linked `OPEN` incident atomically. Rejected/inconclusive candidates create none. **Still pending:** event grouping and duplicate-candidate handling. | The owner approval settles the core flow only; event grouping and formal OAD disposition remain open. Project team. |
| OAD-016 | `Proposed; provider selection pending` | Prefer a short-lived, single-object, operation-scoped grant only if the selected provider supports it; otherwise use a backend-mediated path. Never expose a public or broad permanent credential. | Blocks evidence transfer contract. Backend/security owner and data governance. |
| OAD-017 | `TBD` | Use a dedicated least-privilege `AI_SERVICE` machine identity, separate from human JWTs, with rotation and replay controls. Keep intake disabled until a concrete authenticator is configured and reviewed. | Blocks machine event intake and any machine upload. Security/integration owner. |
| OAD-018 | `Proposed; team approval required` | **Approved scope:** Keep Police/Hospital scopes independent; Hospital acknowledgement/availability differs from simulated dispatch decision and subsequent status. **Still pending:** exact record mapping, states/transitions, actor grants, and incident aggregate rule. The existing proposal that acknowledgement alone does not activate the incident remains. | Request/response routes remain blocked until the contract and scopes are specified. Project team and incident workflow owner, with Police/Hospital representatives. |
| OAD-019 | `Proposed; ingestion mechanism pending` | Require recorded source owner/purpose authorization. Use only controlled demo files with documented rights until a registry owner and input path are approved; no app role is presumed to be the source owner. | Blocks accepted event intake and source administration. Source owner, AI/data-governance owner, project team. |
| OAD-020 | `Proposed; detailed policy pending` | Preserve claim type, origin, source/event, time, uncertainty, verification, and correction history. Do not expose coordinates by default; require AI inferred claims to reference an authorized event. | Blocks location write/read/display; current model lacks external-report origin and competing-claim workflow. Project team and privacy/data-governance owner. |
| OAD-021 | `Proposed; team approval required` | Use an overdue indicator and manual follow-up only. Do not set an invented threshold, transition to `EXPIRED`, or trigger external escalation. | Blocks expiry behavior and its use in incident resolution. Project team and incident workflow owner. |

Outside the OAD register but required for closure, approve audit-reader scope and audit retention/integrity; existing user/role administration and source-registration authority; the exact read fields disclosed to each role; candidate-review assignment/claim semantics; and whether existing enabled scoped reads and assignment commands are authorized for continued use.

## Conflicting or Ambiguous Policies

| Issue | Conflicting or incomplete repository wording | Closure needed |
|---|---|---|
| OAD-018 incident aggregation | OAD-018 says not to aggregate acknowledgement into incident state, while the decision-register recommendation says the first `IN_PROGRESS` assignment may set `RESPONSE_ACTIVE`. These can coexist only if the trigger is stated precisely. | Approve the aggregate rule: acknowledgement has no incident effect; the first transition to `IN_PROGRESS` may set `RESPONSE_ACTIVE`; neither agency update mutates the other assignment. |
| Reviewer assignment | Candidate policy recommends a queue coordinator assigning one reviewer of record, while the current model has no reviewer-assignment entity and the MVP has one final `CandidateReview`. | Choose one named reviewer for the prototype or approve a reviewer assignment/claim design before exposing a multi-reviewer queue. Do not silently let any group member claim every candidate. |
| Verification rationale and checklist | FR-005 and workflow wording call for a decision/rationale; the service requires rejection rationale but verification rationale is optional. The recommended checklist says a rationale for both outcomes, while evidence-media availability is not a current service precondition. | Approve whether rationale is mandatory for both decisions and whether a linked event is sufficient or a validated media asset is required. Do not invent an AI-confidence threshold. |
| Zero-assignment resolution | The workflow proposes `OPEN → RESOLVED` for a no-response outcome. The service accepts an empty assignment set because the all-terminal check is vacuously true, but it only requires a generic nonblank reason. | Explicitly approve or prohibit zero-assignment resolution. Recommended default: allow only to a designated resolver with a distinct `NO_RESPONSE_REQUIRED` reason and audit record. |
| Resolver, closer, and override | The lifecycle policy requires all assignments terminal and has no override implementation; requirements mention a possible approved override. Resolver and closer may or may not be separate people. | Approve action-specific resolver/closer grants, no override for MVP, no reopen, and no direct close from an active state. If role separation is waived for the small prototype, record that explicitly. |
| `EXPIRED` status | The assignment enum/schema knows `EXPIRED`, but no expiry transition or worker exists and the current resolver terminal set excludes it. Some schema/history vocabulary therefore looks more operational than it is. | Treat `EXPIRED` as unavailable until OAD-021 is approved and transition, timeout source, retries, audit, and resolver semantics are implemented. |
| Shared evidence association | FR-006 permits the candidate and resulting incident to reference the same asset. Evidence policy says Police/Hospital access must be independent and candidate verification does not make evidence admissible or globally accessible. | Approve whether the incident gets a reference automatically and require a separate authorization decision for each reader and media operation. No access inheritance by association alone. |
| Location origin and current claim | The service supports one current claim per typed subject; correction updates the current row with history. External reports have no distinct origin type, and concurrent claims have no adjudication workflow. | Approve external origin, supersession/conflict rules, correction authority, and history retention before multi-source location use. |
| AI location capability | The location policy says a machine inferred candidate claim should reference an event and have explicit machine capability authorization; current service shape checks do not require an event reference or apply an `AuthorizationPolicy` to that machine creation path. The machine authenticator and API are currently disabled. | Preserve the disabled route. Before enabling, require a trusted machine principal, mandatory event/candidate relationship, source authorization, and explicit capability policy. |
| Source permission and controlled files | FR-003 permits a registered authorized source or explicitly approved controlled file; OAD-019 proposes a registry and file support but leaves owner/purpose/input mechanism pending. | Approve who documents rights and whether demo files can create accepted events. “Controlled file” must not be treated as consent by itself. |
| Draft requirements versus implementation | The functional-requirements header says none of its behaviors is implemented, while architecture/readiness documents describe selected auth, scoped reads, assignment commands, and domain services as implemented. | Reconcile the requirements baseline before enabling behavior; cite implementation facts separately from policy approval. |
| Enabled actions versus unapproved matrix | The authorization matrix and readiness document label existing incident/assignment capabilities `PROPOSED` or implementation evidence, while describing them as enabled. | The project owner must ratify each already-enabled scope/action or choose to gate it. Do not broaden an existing endpoint based on a proposed matrix row. |

## Recommended Default Decisions

These defaults are conservative options for project-owner review. They are not stakeholder-approved policy.

1. **Identity and access:** Django is the sole policy enforcement point. Keep `ADMIN`, `POLICE`, and `HOSPITAL` as separate human roles, and `AI_SERVICE` as a machine principal. Require an explicit action grant and resource scope in addition to role/membership. Admin has no global incident, candidate, evidence, location, source, or audit access by role alone. Police and Hospital retain independent target membership and assignment scope. AI cannot review candidates, decide incidents, read general evidence, or mutate assignments.
2. **Candidate review:** For the first academic workflow, designate one reviewer identity (or a narrowly named reviewer cohort only if queue assignment/claim ownership is separately specified). Give separate candidate read, start-review, and final-decision capabilities over an explicit source/candidate scope. Keep Police/Hospital out by default. Require event provenance and a short nonblank rationale for verify and reject. Insufficient or contradictory information remains `UNDER_REVIEW`; do not add dismissal, `NEEDS_EVIDENCE`, merge, or reopen states for the first slice. Treat model output and confidence as evidence, never authority.
3. **Event grouping and domain lifecycle:** Preserve distinct DetectionEvents; use stable event identity for idempotent retry. A new event may create a new candidate. Do not automatically merge distinct similar events until a grouping rule is approved. Keep the separate candidate and incident entities; a successful verification creates one linked `OPEN` incident atomically, and rejection creates none.
4. **Incident lifecycle:** Use action-specific resolver and closer permissions; do not infer them from Admin. Require nonblank reasons and all assignments terminal for ordinary resolution; no override or reopening in MVP. If there are no assignments, permit resolution only with an explicit `NO_RESPONSE_REQUIRED` reason and a specifically authorized resolver. Keep `EXPIRED` unavailable. Acknowledge never changes incident status; first `IN_PROGRESS` may set `RESPONSE_ACTIVE`.
5. **Assignments:** A specifically designated manager creates/cancels/reassigns manually, only for an active eligible target and an eligible incident. Require reasoned, audited replacement rather than in-place target change. Police/Hospital users update only their own target assignment. Manual overdue review is the only timeout behavior; no automatic expiry or external escalation.
6. **AI intake and source control:** Use a separate machine authenticator with least privilege, rotation, replay safeguards, and event-level idempotency. Admit only a source with documented permission and an approved purpose. Start with synthetic or expressly authorized controlled files. Do not expose production intake until source ownership, the machine-auth contract, and data retention are approved.
7. **Evidence:** Default to private, unavailable until integrity/type/size checks and required validation pass, with backend authorization per object. Separate metadata from media permission and Police from Hospital scope. Do not assume that a candidate-to-incident link grants all incident participants access. Leave storage provider, media rules, scan requirements, retention, legal holds, deletion authority, and audit-reader access open for explicit approval; do not fabricate durations.
8. **Location:** Keep camera location separate from accident-location claims. Preserve origin, event/source link, time, accuracy/uncertainty, verifier, and correction history. Unknown remains unknown. Hide coordinates until role-specific scope and precision are approved; no map provider is needed for the first workflow. Require an event-linked machine estimate and a designed conflict/supersession path before enabling machine or multi-source writes.
9. **Audit and retention:** Audit actor, action, target, time, outcome, command/request ID, and safe reason code for consequential decisions and denials. Keep sensitive rationale and precise coordinates in protected domain records, not general logs. No purge, evaluation reuse, legal-hold claim, or real-data retention until source owners and institutional governance approve durations and authority.
10. **Prototype boundary:** Use only synthetic or expressly authorized demonstration data; show simulated response/notification labels; provide no real emergency-service credentials, routes, or fallback. A failed or delayed prototype notification must never trigger a real alert.

## Security and Authorization Implications

- **Fail closed:** Candidate review, incident resolution/closure, assignment administration, evidence, location, and source operations with unresolved authority remain unavailable. The authorization contract documents stable 503 policy-unavailable behavior for unresolved operations and 404 concealment for out-of-scope incident/assignment reads. Do not reveal object existence through a policy-denied path.
- **No group-wide bypass:** Apply authentication, active-account, current membership, target organization, object relationship, action, and lifecycle checks on every request. A group label such as `ADMIN` is not `is_superuser` and does not establish global scope. Police membership must not authorize Hospital data or vice versa.
- **Machine separation:** Do not reuse a human JWT for AI_SERVICE. The authenticator is currently unconfigured, so intake fails closed. Machine capabilities should be restricted to authorized event submission and one authorized evidence upload/completion operation, with replay and rate-limit decisions recorded.
- **Evidence confidentiality:** Authorize each metadata and media request separately. Do not expose object keys, signed URLs, public buckets, broad storage credentials, or raw provider responses. Make `EXPIRED`/`DELETED` inaccessible before asynchronous deletion and reconcile object-store state before claiming deletion.
- **Location privacy and integrity:** Treat precise coordinates as sensitive. Distinguish camera position from accident estimates, preserve uncertainty, and do not equate coordinate decimal places with accuracy. The present machine-location service gap makes an explicit capability gate a prerequisite to any route.
- **Audit safety:** Limit audit readers and safe-context fields; do not log secrets, raw media, full request bodies, or unnecessary coordinates/personal data. Audit access, retention, backup integrity, and deletion require their own approval.
- **Existing enabled scope:** The repository documents scoped incident reads and target assignment updates. Before further privileged work, obtain an owner decision that explicitly ratifies their current actor, field, and organization scope. No global Admin visibility should be introduced as a shortcut.
- **Safety:** Keep all notifications and response states simulated. Do not configure external emergency-service integrations or credentials. Use synthetic or explicitly approved data in any demonstration environment.

## Implementation Dependencies

The dependencies run across domains; an early decision in one area does not authorize the next operation.

~~~mermaid
flowchart TD
    Source[OAD-019 source permission] --> Machine[OAD-017 AI_SERVICE identity]
    Machine --> Events[Authenticated DetectionEvents and stable identity]
    Domain[OAD-015 separate event, candidate, incident] --> Events
    Events --> Review[OAD-012 reviewer scope, criteria, final decision]
    Review --> Incident[Atomic VERIFIED candidate and one OPEN incident]
    Incident --> Assignment[OAD-013 manager and target eligibility]
    Assignment --> Independent[OAD-018 independent Police/Hospital histories]
    Independent --> Lifecycle[Resolver/closer policy; OAD-021 expiry remains off]
    Evidence[OAD-002/014/016 provider, access, validation, retention] --> Review
    Evidence --> Incident
    Location[OAD-001/020 origin, precision, correction, conflict] --> Events
    Location --> Review
    Location --> Incident
    Audit[Audit scope, retention, safe logging] -.cross-cuts.-> Review
    Audit -.cross-cuts.-> Incident
    Audit -.cross-cuts.-> Independent
~~~

Specific ordering constraints:

- **Source and event intake precede review.** Source owner/purpose authorization (OAD-019), machine authentication (OAD-017), event identity/provenance, and candidate association rules must be settled before accepted AI intake. OAD-003/004/005 affect what the observation means, not who may decide.
- **Candidate review gates incident creation.** OAD-015 defines separate records; OAD-012 defines human actor, scope, checklist, one-versus-multiple decisions, rationale, and conflict handling. Verification must remain atomic with creation of one incident. Evidence sufficiency and location interpretation feed the checklist but do not replace human authority.
- **Incident creation precedes agency work.** OAD-013 establishes who may create/cancel/reassign and which targets are eligible. OAD-018 preserves independent assignments and clarifies the aggregate `RESPONSE_ACTIVE` trigger. OAD-021 is required before any expiry transition or use of `EXPIRED` in the resolver terminal set.
- **Resolution and closure need independent authority.** OAD-012/OAD-018 and FR-022/023 must settle resolver/closer scope, all-terminal behavior, no-assignment handling, override, and reopening before those routes are enabled.
- **Evidence and location cross-cut the entire path.** Evidence access, provider, integrity, transfer, retention, deletion, and candidate-to-incident sharing (OAD-002/014/016) determine what reviewers and agencies can see. Location origin, precision, corrections, and conflicts (OAD-001/020) determine what can be collected or displayed at each stage. Neither should inherit authority merely because an incident exists.
- **Audit, source consent, and retention are cross-cutting gates.** Audit access/retention and source rights apply before real data collection, privileged transitions, or automated deletion.

## Testable Acceptance Criteria

The following criteria must be turned into implementation tests before a governed workflow is enabled. They are proposed tests, not tests run by this review.

1. **Approval traceability:** Every enabled privileged action maps to a dated, recorded owner decision (ADR or dated OAD amendment), actor type, resource scope, state preconditions, denial behavior, and related requirement. Draft/proposed/TBD entries do not enable an action.
2. **Role and scope isolation:** Only a specifically authorized Police reviewer in the approved candidate scope can review/decide; Police group membership alone does not grant access. An Admin without an explicit grant cannot read arbitrary candidates, incidents, evidence, locations, sources, or audit. Police and Hospital response access remains limited to the matching active organization/request/assignment. Cross-organization and inactive-membership attempts fail without data leakage.
3. **Machine identity:** A human JWT cannot authenticate as AI_SERVICE. An unconfigured, revoked, replayed, or out-of-scope machine request creates no event, candidate, location, or evidence mutation. A valid machine request cannot read candidate queues, decide candidates, create incidents, access general evidence, or update assignments.
4. **Source and event integrity:** An event from an unauthorized/revoked source is rejected. A retry with the same source/event identity and same canonical payload is idempotent; a conflicting payload under the same identity is rejected. Distinct observations remain individually traceable and are not silently merged.
5. **Candidate authority and lifecycle:** Only an approved human reviewer within candidate scope can start and finalize review. Insufficient/contradictory evidence leaves the candidate `UNDER_REVIEW`. Verify and reject require the approved rationale/checklist. Machine actors cannot decide. Invalid/stale final commands fail without changing state; concurrent finalization produces at most one final review and one linked incident.
6. **Atomic incident creation:** A successful verification creates exactly one `OPEN` incident, review, histories, and success audit in one transaction. Injected transaction failure leaves no `VERIFIED` candidate or orphan incident. A matching retry is idempotent; a mismatched command ID conflicts. Rejection creates no incident.
7. **Assignment independence:** The Hospital request is created only after the verified incident commits and is linked to that incident and the designated Hospital. Request retries do not duplicate the incident or request. Updating, cancelling, or replacing one assignment never changes another target’s history. Acknowledgement does not move the incident to `RESPONSE_ACTIVE`; the first approved `IN_PROGRESS` transition does. Hospital availability, simulated dispatch, and subsequent response status are distinct. Agency completion never resolves or closes the incident.
8. **Incident resolution:** Only the designated resolver can resolve an eligible incident; the ordinary path rejects any nonterminal assignment and requires a nonblank reason. If zero-assignment resolution is approved, only the explicit `NO_RESPONSE_REQUIRED` reason permits it. Closure requires `RESOLVED`, an authorized closer, and a reason. Reopen, override, and `EXPIRED` are denied until separately approved and implemented.
9. **Timeout and simulation:** No timeout threshold is active absent an approval. Manual overdue follow-up does not mutate assignment state. Notification, read, failure, retry, and response activity remain labeled simulated and cannot produce an outbound emergency request or dispatch.
10. **Evidence access and lifecycle:** Evidence is private. Metadata and media each require current object-level permission; Police and Hospital authorization is independently evaluated. Only validated `AVAILABLE` assets are retrievable. Candidate/incident association alone does not grant access. Expiry immediately denies retrieval; deletion is recorded only after external absence is confirmed; failure leaves the asset inaccessible and reconcilable.
11. **Location provenance:** Camera-position claims are never presented as accident location. Inferred claims identify their source event and uncertainty. Missing capture time/accuracy stays unknown. Role-specific reads do not exceed approved precision. Corrections preserve old/new values, actor, time, and rationale; conflicting claims follow an approved, auditable supersession rule.
12. **Audit and retention:** Successful and denied sensitive actions produce safe actor/action/resource/time/outcome/correlation records. Tests verify that credentials, tokens, media bytes, signed URLs, unrestricted request bodies, and unnecessary precise coordinates are absent. Retention, legal hold, deletion, evaluation reuse, and backup restore follow the approved policy without silently removing provenance.
13. **Existing enabled operations:** Tests and policy records confirm or revoke the current scoped incident reads and target-assignment updates, including exact fields, current-membership checks, active assignment requirements, concealment behavior, and absence of Admin global bypass.

## Project Owner Approval Checklist

No names are recorded in the repository for these approver roles. The project owner should assign actual people, collect explicit decisions, and record the result without changing a status based on this review alone.

- [ ] Ratify the architecture and requirements baseline; record which draft documents become authoritative.
- [ ] Ratify or gate the already-enabled scoped incident reads and Police/Hospital assignment commands; approve exact fields and scopes.
- [x] Project-owner task approval (2026-11-19): Police-first review by an appropriately authorized human Police reviewer; atomic single `OPEN` incident on verification; no incident/request for rejected or inconclusive candidates; post-commit Hospital request; separate Hospital acknowledgement/availability and simulated dispatch/status; independent scope/audit; synthetic or authorized inputs; no external contact. This is workflow approval, not a runtime grant.
- [x] Project-owner task approval (2026-11-19): Keep notifications, acknowledgements, dispatch decisions, and response outcomes simulated in the academic prototype; no real Police/Hospital/ambulance/emergency-service contact.
- [x] Project-owner approved scope under OAD-015: retain distinct `DetectionEvent`, `AccidentCandidate`, and `AccidentIncident`; no AI-created verified incident.
- [ ] Complete OAD-015 event-grouping and duplicate-candidate rules; preserve the existing OAD status entry until formal disposition.
- [ ] Complete OAD-012 reviewer identity/scope, candidate visibility, review assignment/claim model, decision count, verification checklist, rationale for each outcome, insufficient/contradictory evidence, and correction/reopen handling.
- [ ] Approve OAD-005/003/004: AI method, model/tracking choice, approved evaluation data, measures, and limitations; confirm AI output is not decision authority.
- [ ] Approve OAD-017/019: AI machine-auth mechanism and lifecycle, source-owner consent evidence, source registry authority, controlled-file rules, and event identity contract.
- [ ] Complete OAD-013/018: who designates the Hospital, target eligibility/routing, request-to-assignment mapping, create/cancel/reassign rules, Hospital response states/transitions, independent histories, and incident `RESPONSE_ACTIVE` aggregation trigger.
- [ ] Approve incident resolver/closer actor and scope, whether the same person may hold both permissions, no-assignment resolution, terminal assignment rule, override, reopening, invalidity, and post-close correction.
- [ ] Approve OAD-021: keep manual overdue handling or specify timeout threshold, clock/retry behavior, `EXPIRED` transition, audit, and resolver treatment; confirm no external escalation.
- [ ] Approve OAD-002/016: evidence provider, transfer/retrieval method, media/type/size/scanning policy, fields by role, candidate-to-incident reference/access semantics, and validation criteria.
- [ ] Approve OAD-014: source, candidate, rejected case, incident, evidence, location, audit, evaluation-copy, backup, and legal-hold retention; deletion requester/approver and recovery process.
- [ ] Approve OAD-001/020: location claim origin/owner, external reports, required event links, role-specific precision, read/display scope, verification/correction authority, competing claims, and history retention.
- [ ] Approve source data classification, audit-reader scope/integrity/retention, account/role administration, and any administrative reporting scope.
- [x] Project-owner task approval (2026-11-19): use synthetic or expressly authorized test events and prohibit external Police, Hospital, ambulance, and emergency-service contact.
- [ ] Record the approver, date, decision status, rationale, related OAD/FR/NFR, and any implementation consequences for each accepted or rejected recommendation.

## Implementation Readiness Assessment

**Not ready for privileged incident-management implementation.** The owner has approved the workflow sequence, but the action-specific identities, scopes, Hospital routing, and state contracts required to implement it are not yet complete. The previous readiness finding is therefore partially resolved at workflow level only.

| Capability | Readiness |
|---|---|
| Candidate queue/review/verify/reject | Police reviewer role/order approved; blocked on OAD-012 reviewer identity, scope, criteria, permitted fields, and conflict decisions. |
| AI event intake | Blocked on OAD-017 machine authentication and OAD-019 source permission/input rules. |
| Incident create after verification | Domain service exists; activation remains blocked on approved human authority and approved candidate policy. |
| Incident resolve/close | Blocked on resolver/closer authority, no-assignment outcome, terminal rule, and override/reopen decisions. |
| Post-verification Hospital request | Workflow trigger approved; target/routing, request mapping, retry contract, and route remain blocked on OAD-013/OAD-018. |
| Hospital acknowledgement and simulated response | Workflow concepts approved; exact state vocabulary, scope, history/API contract, and simulated dispatch status route remain blocked. |
| Assignment cancel/reassign | Blocked on OAD-013/OAD-018; routes fail closed. |
| Evidence upload/retrieval/deletion | Blocked on OAD-002/014/016, provider/verifier, role scope, validation, retention, and deletion authority. |
| Location create/read/verify/correct/display | Blocked on OAD-001/020, precision/access, claim conflict handling, and machine capability gap. |
| Assignment expiry | Not implemented; OAD-021 unresolved; `EXPIRED` must remain unusable. |
| Real emergency dispatch | Prohibited for this prototype. |

Non-privileged documentation and isolated synthetic-fixture engineering may continue, but no route, policy grant, or operational dataset should be enabled by relying on the recommendations in this report. Keep existing fail-closed behavior until the owner records the required approvals.

## Recommended Next Implementation Sequence

1. **Record governance outcomes.** Assign real decision owners, resolve the checklist, and write dated OAD amendments/ADRs. Preserve current OAD identifiers and statuses until the approving owner records a decision.
2. **Freeze the approved demo boundary.** Confirm synthetic or expressly authorized inputs, local/institution-controlled environment, data retention, no live providers, and no external emergency delivery.
3. **Close intake prerequisites.** Approve source authorization, AI_SERVICE authentication, event identity/retry behavior, and whether deterministic fixture events or an evaluated detector will supply the first workflow.
4. **Implement the approved Police verification slice.** Accept one scoped, authenticated demo DetectionEvent; create or explicitly associate its candidate; let only the designated Police reviewer inspect approved information and decide; record the decision; atomically create one linked `OPEN` incident on verification and none on rejection/inconclusive review.
5. **Add the approved Hospital response slice after remaining OAD-013/018 decisions.** Create an incident-linked request for the designated Hospital only after incident commit; make request creation idempotent and recoverable; allow only the exact Hospital scope to record acknowledgement and availability/inability; record simulated dispatch decision and response status separately; provide scoped tracking. Test independent histories and ensure no real external contact.
6. **Add incident resolution/closure.** After resolver/closer, no-assignment, terminal-set, and override decisions are approved, implement the explicit reasoned transitions and their transaction, idempotency, concurrency, and audit behavior. Leave reopening and expiry disabled unless separately accepted.
7. **Add evidence and location as separately governed capabilities.** Implement their providers/contracts, object/claim-level permissions, integrity and conflict workflows, retention/deletion/recovery, and role-specific fields only after the relevant privacy and data owners approve them.
8. **Complete security and operational review before enabling the workflow beyond isolated demonstration.** Verify negative role/scope cases, cross-organization isolation, atomic rollback, request/command idempotency, audit redaction, retention recovery, and the no-dispatch boundary. Review configuration and egress to confirm that no external emergency channel is reachable.

### Original Review Validation Record (3c26c96)

- Baseline branch and commit: `main` / `3c26c96541b9b97ead4b70608e580e28dd52cd58`.
- The architecture README’s local references and all local Markdown links in `docs/architecture/**` plus the ADR index resolved during review.
- OAD identifiers OAD-001 through OAD-021 were checked against the existing register; none was renamed or approved by this review.
- The requested report path did not exist before this review. This report is the only file created. No application code, tests, models, migrations, APIs, permissions, or authentication behavior were changed. No tests were run.
- `git diff --check` passed. The untracked-file `git diff --no-index --check -- /dev/null <report>` check emitted no whitespace findings (its exit code is `1` because the report differs from an empty file). `git diff --name-only` is empty.
- Final `git status --short --branch --untracked-files=all` is `## main...origin/main` plus only `?? docs/architecture/decisions/domain_governance_approval_review.md`. The review is not committed.

### Workflow Update Validation Record (starting baseline 879438f)

- The project-owner workflow supplied on 2026-11-19 was recorded as an approved workflow slice. No OAD identifiers or OAD status entries were changed; unresolved details remain explicit.
- Created `docs/architecture/domain/accident_verification_emergency_response_workflow.md`.
- Updated `docs/architecture/README.md`, `docs/architecture/data_flow.md`, `docs/architecture/decisions/domain_governance_approval_review.md`, `docs/architecture/decisions/domain_governance_decision_register.md`, `docs/architecture/domain/candidate_review_verification_policy.md`, `docs/architecture/domain/domain_principles.md`, `docs/architecture/domain/governance_overview.md`, `docs/architecture/domain/implementation_readiness.md`, `docs/architecture/domain/incident_lifecycle_policy.md`, `docs/architecture/security/authorization_matrix.md`, `docs/requirements/functional_requirements.md`, `docs/requirements/requirements_traceability.md`, `docs/requirements/role_permission_matrix.md`, `docs/requirements/use_cases.md`, `docs/workflows/incident_response_workflow.md`, and `docs/workflows/system_workflow.md`.
- No Django or Flutter source, API, permission implementation, authentication behavior, model, migration, or test file was changed. No tests were run.
