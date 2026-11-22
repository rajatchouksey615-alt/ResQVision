# Candidate Review Implementation Readiness

**Readiness verdict:** The approved governance baseline now includes the 2026-11-22 candidate-intake, routing, and assignment rules, but candidate review is **not ready for privileged end-to-end implementation or enabled routes**. Production intake authentication, event eligibility, route-data maintenance, runtime organization/reviewer binding, and `FURTHER_REVIEW` support remain unresolved or unimplemented. Keep current fail-closed runtime behavior.
**Policy approvals recorded:** Project owner, 2026-11-21 and 2026-11-22. Related existing OADs: OAD-005, OAD-012, OAD-015, OAD-019. Their overall statuses remain unchanged; see the [domain governance decision register](../decisions/domain_governance_decision_register.md).
**Scope:** Documentation and governance readiness for Police candidate intake, assignment, listing/review, decisions, one verified incident, Flutter integration, audit, and end-to-end verification. No application implementation is authorized by this assessment.

**Candidate intake and assignment architecture:** The owner-approved policy slices are documented in the [Candidate Intake and Police Assignment Architecture](candidate_intake_assignment_architecture.md). Event eligibility details, production AI authentication, route-data maintenance, duplicate policy, and detailed `FURTHER_REVIEW` lifecycle recommendations remain proposals or dependencies; no OAD overall status changed.

## Approved Candidate Review Policy Baseline

- Only the specifically assigned and authorized human Police reviewer may review a candidate, with active membership in the Police organization to which the candidate is assigned. Access is limited to that assigned candidate.
- Candidate assignment must be made by an explicitly authorized authority within the relevant Police organization. No whole-`POLICE` group access, unrestricted Admin bypass, or new human role is approved.
- Only an authorized human Police reviewer records decisions. AI detection never independently establishes an accident.
- Allowed outcomes are `VERIFIED`, `REJECTED`, and `FURTHER_REVIEW`. `VERIFIED` creates exactly one authoritative `OPEN` `AccidentIncident`; `REJECTED` creates none; `FURTHER_REVIEW` creates none and preserves the candidate for subsequent review.
- Verification and incident creation are atomic and safe against duplicate or concurrent requests. Candidate assignment, review, decisions, and incident creation are traceable in audit records.
- The backend creates candidates from eligible events; AI cannot verify an accident or select a reviewer. Each authorized video source has exactly one designated active Police organization, with routing determined by the backend. Missing, inactive, or non-unique routing fails closed. Assignment authority is limited to an authorized `ADMIN`-group user with active Police membership in the candidate's organization assigning an active Police reviewer in that same organization. These approvals do not enable runtime routes or grant global Admin access.

The project owner separately approved a simulated Hospital response sequence on 2026-11-19. That workflow does not expand this candidate-review scope: Hospital requests/notifications, acknowledgement, ambulance dispatch/status, and any external agency communication are excluded here. No real emergency contact is in scope.

## Existing Runtime Compatibility

| Capability | Existing behavior | Candidate-review readiness |
|---|---|---|
| Detection event intake | `DetectionEvent` stores event and source provenance; `(video_source, external_event_id)` is unique. AI API authentication is unconfigured and ingestion fails closed. | The approved candidate-creation policy does not authorize unauthenticated production submission. Configure a reviewed machine identity, source grants, and replay controls under OAD-017/OAD-008 before enabling intake. |
| Event-to-candidate materialization | `create_candidate` requires an explicitly selected event; event ingestion does not automatically create candidates. There is no public candidate creation API. The service requires an authorized source and deduplicates an already-associated event. Its `MachineActor` path does not invoke the candidate creation authorization policy. | **Policy approved; implementation blocked.** Define which events are eligible and the duplicate/grouping boundary. Implement a backend materializer with source, route, policy, and audit checks; do not expose the current service path as-is. |
| Police source routing | `VideoSource` has optional source-owner organization; it has no Police route. Candidates have no organization binding. | **Policy approved; implementation blocked.** Add a backend-resolved route satisfying exactly one designated active Police organization per authorized source. Missing, inactive, or non-unique routing must create no candidate. Decide who may maintain/correct route data. |
| Police candidate assignment | No candidate-to-Police-organization or assigned-reviewer fields, assignment service, or assignment route exist. | **Authority rule approved; implementation blocked.** Enforce the approved `ADMIN`-group plus active membership in the exact Police organization for the assigner, and require an active Police reviewer from that same organization. Do not grant global Admin privileges. |
| Candidate queue/detail | Selectors and policy hooks exist, but no candidate authorization policy is configured. `HasCandidateReviewPermission` denies; list/detail routes return policy-unavailable. The selector has no assignment or organization scope. | Blocked. Implement only after candidate-to-organization/reviewer binding and the approved active-membership/assigned-candidate scope are enforced on every request. |
| Review start | `begin_candidate_review` locks the candidate, checks an injected policy, moves `RECEIVED` to `UNDER_REVIEW`, and audits. It has no reviewer assignment or organization check; it rejects a second start when already `UNDER_REVIEW`. | Partial technical foundation; blocked pending assignment scope and three-outcome lifecycle support. |
| `VERIFIED` outcome | Human-only service writes final review, candidate state, one linked `OPEN` incident, initial incident history, and success audit inside a transaction. Candidate row lock, command ID, and unique constraints defend retries/concurrency. | Approved invariant matches existing behavior and is reusable. Keep inaccessible until reviewer authorization is enforced. |
| `REJECTED` outcome | Human-only final decision sets candidate `REJECTED`, writes audit, and creates no incident. Runtime requires a nonblank rejection rationale; verification rationale is optional. | No-incident outcome matches. Rationale requirements were not specified in the 2026-11-21 approval; retain current behavior and do not present it as a newly approved rule. |
| `FURTHER_REVIEW` outcome | Not present in `ReviewDecision`; no non-final decision record/action exists. Candidate can remain `UNDER_REVIEW`, but the service cannot record this outcome and then begin a subsequent review. | Blocked. The approved outcome needs a persisted/traceable representation and a subsequent-review path that preserves the candidate without creating an incident. |
| Audit | Existing audit covers candidate creation/association, review start, final verify/reject, and verified incident ID. There is no candidate-assignment or `FURTHER_REVIEW` audit event. | Partial. Add assignment and further-review audit records with safe, attributable fields before claiming full coverage. Audit reader scope/retention are separate open governance matters. |
| Flutter review experience | Authenticated API client, role/membership data, dashboards, and incident read patterns exist. No candidate review UI or backend contract exists. | Reusable client foundation only. Functional review screens are blocked until backend authorization and request/response contracts are established. |
| Audit and end-to-end verification | Existing backend/domain and mobile test infrastructure is available; candidate route and user journey are unavailable. | Future acceptance work after implementation. This documentation task did not modify or run tests. |

## Unresolved Architecture Questions and Gates

These questions remain prerequisites to the corresponding candidate-review capabilities:

| Open question | Existing decision / owner-approved boundary | Gate before implementation |
|---|---|---|
| Which `DetectionEvent`s are eligible for candidate creation, and what is the duplicate boundary? | OAD-005/OAD-015; backend candidate creation from eligible events is approved, but eligible outcomes and cross-event grouping are not specified. | Define the eligibility predicate, provenance/cardinality, and exact-event versus cross-event duplicate behavior before broad intake. |
| What production authentication should AI use to submit events? | OAD-017/OAD-008; machine authentication and transport are not configured. | Select and configure a separate, least-privilege machine identity, source grants, credential lifecycle, and replay controls before enabling intake. |
| Who may maintain or correct a source's Police route? | OAD-019/OAD-012; the one-active-Police-route invariant and backend routing are approved. | Define route-data maintenance and correction authority, storage, and audit before enabling route configuration. Routing must fail closed if missing, inactive, or non-unique. |
| How should the approved candidate assignment rule be represented and enforced? | OAD-012; the `ADMIN` group plus active membership in the candidate's exact Police organization, and a same-organization active Police reviewer, are approved. | Implement assignment records, server-side checks, and audit; do not grant global Admin or add a role. |
| Does `CandidateReview` support all three outcomes? | OAD-015; all outcomes and their incident consequences are approved; exact `FURTHER_REVIEW` lifecycle details are not. | No. Current model/service supports only final `VERIFIED`/`REJECTED`. Add an audited non-final history and subsequent-review path after its state and assignment semantics are resolved. |

Candidate-to-Police-organization/reviewer scope and permitted response fields also need to be represented before listing/detail routes can safely operate. The model currently has no such assignment relationship, and existing evidence/media/location references do not inherit access from candidate assignment. Do not widen review data beyond separately approved fields.

## Candidate Intake and Assignment Implementation Gates

The backend materializer principle, Police routing invariant, and scoped assignment authority are approved. The following rows distinguish those decisions from remaining proposals and implementation work.

| Proposed capability | Recommendation | Approval and implementation gate |
|---|---|---|
| AI event authentication and source scope | Dedicated machine identity with short-lived credentials and explicit source grants; OAuth 2.0 client credentials is a proposal where deployment supports it. | Backend/security review and an identified issuer or reviewed alternative are required under OAD-017/OAD-008. Keep event submission fail-closed until configured. |
| Event-to-candidate eligibility and deduplication | Treat both current event outcomes as non-final candidate intake; one candidate per eligible event; no automatic merge of distinct event IDs. | These remain proposed policy choices under OAD-005/OAD-015; owner approval is required before treating them as rules. |
| Police route maintenance | Use a server-managed source-to-Police mapping and validate it resolves to exactly one active Police organization. | The routing invariant is approved under OAD-019/OAD-012. Define who may configure/correct the mapping and its audit before implementation. Missing, inactive, or non-unique mapping fails closed. |
| Reviewer assignment representation and cardinality | Implement the approved `ADMIN`-group plus exact-organization active membership rule and same-organization active Police target; decide whether one current reviewer is required and how reassignment works. | Authority rule is approved under OAD-012. Assignment records, authorization checks, audit, cardinality, and reassignment remain implementation or policy work. No global Admin access or new role. |
| `FURTHER_REVIEW` persistence | Append non-final decision history, return candidate to `RECEIVED`, retain the assignee, and allow another review cycle without an incident. | The outcome/no-incident/preservation meaning is approved; state, assignment, persistence, and idempotency details remain proposed under OAD-012/OAD-015. |
| Assignment/routing/FURTHER_REVIEW audit | Add safe allow-listed actions and commit successful audit with domain state. | Backend/security owner approves event and context fields; project owner confirms alignment with the approved traceability requirement. |

The full recommendation, current-code evidence, error handling, and exact approval boundaries are in the [architecture design](candidate_intake_assignment_architecture.md) and [decision proposal](../decisions/candidate_intake_assignment_decision_proposal.md). Preserve existing OAD identifiers and statuses while pending; do not use OAD-013 for reviewer assignment.

## Candidate Review Readiness by Work Item

| Work item | Readiness |
|---|---|
| Candidate intake and creation | **Policy approved; implementation blocked** pending event eligibility, production AI authentication/source grants, routing enforcement, and duplicate policy. Existing event/candidate services are reusable only behind those controls. |
| Authorized Police candidate assignment | **Authority approved; implementation blocked** pending candidate organization/reviewer binding, assignment records, server-side enforcement, and audit. |
| Police listing, detail, and review | **Blocked** pending server-side assigned-candidate + active-organization policy and field scope. No global Police queue. |
| `VERIFIED` / `REJECTED` decisions | **Policy approved; runtime blocked.** Existing service outcomes are compatible with the incident/no-incident rules, subject to the unconfigured reviewer policy and existing rationale behavior. |
| `FURTHER_REVIEW` | **Policy approved; implementation blocked.** Current model/service cannot persist it or support subsequent review. |
| Exactly one `OPEN` incident after verification | **Existing technical path is reusable and compatible.** Its API remains blocked until candidate access and decision authority are enforced. |
| Flutter integration | **Blocked for functional review flows** until backend contract and authorization are available. Existing authenticated client patterns may be reused afterward. |
| Audit and end-to-end testing | **Partially ready.** Existing trace covers several actions; assignment and `FURTHER_REVIEW` audit coverage are missing. Run future acceptance tests after contracts are implemented; no tests were run for this documentation-only work. |

## Candidate Review Entry Decision

**Do not begin privileged end-to-end candidate-review implementation yet.** The 2026-11-22 approvals settle candidate-creation authority, the Police-routing invariant, and the reviewer-assignment authority rule; they do not configure or implement those controls. Resolve production machine authentication/source grants, event eligibility and duplicate boundaries, route-data maintenance, and detailed `FURTHER_REVIEW` semantics. Then implement backend checks, API contracts, audit behavior, Flutter behavior, and acceptance criteria. Keep candidate endpoints and runtime permissions fail-closed until the controls are implemented and verified.

The verified-incident transaction, rejection no-incident path, source-event identity constraints, existing audit allowlist, and Flutter authenticated client are available for reuse. They do not by themselves make the end-to-end feature ready.

## Out of Scope

Hospital notification/request creation, Hospital acknowledgement, ambulance dispatch/status, evidence upload/retrieval policy, location display/correction, incident resolution/closure, assignment expiry, external agency contact, and live emergency response are outside the candidate-review implementation scope assessed here.
