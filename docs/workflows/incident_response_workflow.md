# Incident Response Workflow

**Status:** REVISED_DRAFT — pending team approval. Police-first simulated response order was approved on 2026-11-19; the assignment-scoped candidate review policy, three outcomes, atomic verified-incident invariant, and audit requirement were approved on 2026-11-21. Runtime contracts remain blocked. Hospital response is outside candidate review.

## Candidate Lifecycle

| State | Meaning | Allowed transition and actor |
|---|---|---|
| RECEIVED | Candidate was created through an approved intake/materialization path and has event provenance | Assignment is made by an explicitly authorized authority within the relevant Police organization; intake mechanism remains unresolved |
| UNDER_REVIEW | Candidate is assigned and available to its specifically assigned authorized Police reviewer with active membership in the assigned organization | Reviewer may record `VERIFIED`, `REJECTED`, or `FURTHER_REVIEW`; no group-wide access |
| VERIFIED | Assigned authorized human Police reviewer recorded `VERIFIED` | Backend atomically creates exactly one linked `OPEN` AccidentIncident; AI cannot decide; Hospital request is a separately governed later workflow |
| REJECTED | Assigned authorized human Police reviewer recorded `REJECTED` | No incident is created. Existing runtime requires rejection rationale; the 2026-11-21 policy did not add that requirement. |
| FURTHER_REVIEW (decision outcome) | Assigned authorized human Police reviewer records that subsequent review is needed | No incident; preserve the candidate for subsequent review and audit the outcome. This is not currently supported by the model/service. |

AI detection is an observation and never independently establishes an accident. Only the specifically assigned and authorized human Police reviewer with active membership in the candidate's assigned Police organization may access/review it. Assignment is performed by an explicitly authorized authority within that organization. No whole-`POLICE` access, unrestricted Admin bypass, or new human role is approved. The candidate-to-organization/reviewer binding and assignment authority mechanism remain unresolved. The event-to-candidate trigger/grouping path also remains unresolved; duplicate source/event identity handling does not solve it. See the [candidate review policy](../architecture/domain/candidate_review_verification_policy.md) and [decision register](../architecture/decisions/domain_governance_decision_register.md).

~~~mermaid
stateDiagram-v2
    [*] --> RECEIVED: approved intake materializes candidate
    RECEIVED --> UNDER_REVIEW: candidate queued for human review
    UNDER_REVIEW --> VERIFIED: assigned authorized Police reviewer
    UNDER_REVIEW --> REJECTED: assigned authorized Police reviewer
    UNDER_REVIEW --> UNDER_REVIEW: FURTHER_REVIEW; preserve candidate
    VERIFIED --> [*]: linked OPEN AccidentIncident created
    REJECTED --> [*]: retained for audit/evaluation policy
~~~

### Candidate Transition Table

| From | To | Actor/guard | Required audit |
|---|---|---|---|
| No candidate | RECEIVED | Backend only after approved intake/materialization; event association rule unresolved | Event/source identity, actor/service, outcome |
| Candidate unassigned | Assigned to Police reviewer | Explicitly authorized authority within relevant Police organization; specific mechanism unresolved | Authority, candidate, organization, assigned reviewer, time/outcome |
| RECEIVED | UNDER_REVIEW | Candidate assigned to authorized reviewer; active membership/scope checked | Reviewer, candidate, state, time, outcome |
| UNDER_REVIEW | VERIFIED | Specifically assigned and authorized human Police reviewer with active membership | Reviewer, decision, time/outcome, command; incident ID |
| UNDER_REVIEW | REJECTED | Same assigned reviewer scope | Reviewer, decision, time/outcome, command; no incident ID |
| UNDER_REVIEW | FURTHER_REVIEW | Same assigned reviewer scope; keep candidate for subsequent review | Reviewer, outcome, time, command; no incident ID |

No direct transition from RECEIVED to a decision outcome or from REJECTED back to active review is in the current model. `FURTHER_REVIEW` is an approved outcome but its persistence/subsequent-review implementation is missing. Corrections/reopening require a separate decision.

## Candidate Verification and Incident Creation

~~~mermaid
sequenceDiagram
    participant AI as AI_SERVICE
    participant API as Backend
    participant DB as PostgreSQL
    actor Authority as Explicitly authorized Police organization authority
    actor Reviewer as Specifically authorized Police reviewer
    AI->>API: Submit DetectionEvent(s) and evidence references
    API->>API: Authenticate machine identity, validate source/provenance, deduplicate event ID
    API->>API: Apply approved intake/materialization policy (currently unresolved)
    API->>DB: Create/associate candidate only when authorized by that policy
    Authority->>API: Assign candidate within relevant Police organization
    API->>API: Check assigned reviewer and active Police membership
    Reviewer->>API: Submit VERIFIED, REJECTED, or FURTHER_REVIEW
    alt REJECTED
        API->>DB: Record REJECTED and audit; no incident
    else FURTHER_REVIEW
        API->>DB: Record FURTHER_REVIEW and audit; preserve candidate; no incident
    else VERIFIED
        API->>DB: Atomic commit: VERIFIED candidate + linked OPEN AccidentIncident + histories/audit
    end
~~~

If the verification/incident transaction fails, neither a falsely VERIFIED candidate nor an orphan incident is committed. Retrying the same decision must not create a second incident. `REJECTED` and `FURTHER_REVIEW` create no incident; further review preserves the candidate for subsequent review. The approved Hospital request/response workflow is separate from candidate review.

## Incident Lifecycle

| State | Meaning | Proposed transition rule |
|---|---|---|
| OPEN | Authoritative incident created from a verified candidate | Remains OPEN until response activity starts |
| RESPONSE_ACTIVE | At least one ResponseAssignment has entered IN_PROGRESS | Set from response activity, not from Notification delivery or assignment acknowledgement |
| RESOLVED | Authorized incident-level decision records the outcome | Proposed prerequisite: all assignments are terminal or an explicit authorized override records outstanding exceptions |
| CLOSED | Separate authorized closure review is complete | Requires RESOLVED, actor, and closure reason |

### Incident Transition Table

| From | To | Actor/guard | Required audit |
|---|---|---|---|
| No incident | OPEN | Backend only, atomically with authorized candidate VERIFIED | Candidate reference, reviewer decision, creation time, actor/service |
| OPEN | RESPONSE_ACTIVE | Backend when first assignment enters IN_PROGRESS | Trigger assignment and response event |
| OPEN | RESOLVED | Authorized incident resolver with documented no-response/outcome reason | Actor, reason, assignment outcome summary |
| RESPONSE_ACTIVE | RESOLVED | Authorized incident resolver after assignments are terminal, or approved override with reason | Actor, reason, terminal statuses/override |
| RESOLVED | CLOSED | Separately authorized closure actor after review | Actor, closure reason, time |

All other transitions are denied and audited. Assignment/notification state is not copied into incident status.

~~~mermaid
stateDiagram-v2
    [*] --> OPEN: verified candidate creates incident
    OPEN --> RESPONSE_ACTIVE: first assignment enters IN_PROGRESS
    RESPONSE_ACTIVE --> RESOLVED: authorized incident resolver records outcome
    OPEN --> RESOLVED: authorized resolver records no-response/administrative outcome
    RESOLVED --> CLOSED: authorized closure review and reason
    CLOSED --> [*]
~~~

The incident lifecycle never uses PENDING, ACKNOWLEDGED, COMPLETED, or other assignment states. Proposed resolution rule: nonterminal assignments must be completed, marked unable, cancelled, or expired under an approved policy before RESOLVED. A documented override requires separate approval. Resolver, closer, reopen, and post-close correction authority remain team decisions. Default behavior is to deny reopening until approved.

The project-owner-approved workflow places the Hospital request after the `OPEN` incident is committed. Hospital acknowledgement and availability/inability are separate from a simulated ambulance-dispatch decision and subsequent simulated response status. No ambulance activity is an `AccidentIncident` state, and no real dispatch occurs. The exact request record, state vocabulary, actor grants, and tracking fields remain pending; see the linked governance workflow.

## Independent ResponseAssignment Lifecycle

Each ResponseAssignment links one AccidentIncident to one eligible Police or Hospital target. A single incident may have multiple assignments; each has its own acknowledgement, state history, and Response activity.

| State | Meaning | Proposed allowed next states |
|---|---|---|
| PENDING | Assignment exists, no acknowledgement | ACKNOWLEDGED, UNABLE_TO_RESPOND, CANCELLED; EXPIRED only under approved timeout policy |
| ACKNOWLEDGED | Assigned user acknowledged this assignment | IN_PROGRESS, COMPLETED, UNABLE_TO_RESPOND, CANCELLED |
| IN_PROGRESS | Assigned user recorded a simulated response activity | COMPLETED, UNABLE_TO_RESPOND, CANCELLED |
| COMPLETED | This target's prototype workflow is complete | Terminal |
| UNABLE_TO_RESPOND | Target explicitly cannot handle the assignment; reason required | Terminal unless a new assignment is created |
| CANCELLED | Authorized actor cancelled this assignment | Terminal; reassignment creates a new assignment |
| EXPIRED | Approved timeout policy expired the assignment | Terminal; do not use without policy approval |

### Assignment Transition Table

| From | To | Actor/guard | Required audit |
|---|---|---|---|
| No assignment | PENDING | Authorized assignment actor; verified incident and eligible target | Creator, target, incident, reason/time |
| PENDING | ACKNOWLEDGED | Authenticated user assigned to this exact target | User, target, acknowledgement time |
| PENDING/ACKNOWLEDGED/IN_PROGRESS | UNABLE_TO_RESPOND | Assigned target user; reason required | User, target, reason/time |
| PENDING/ACKNOWLEDGED/IN_PROGRESS | CANCELLED | Authorized assignment actor only | Actor, reason, prior state/time |
| PENDING | EXPIRED | Backend only, only after timeout policy approval | Policy/version, timeout, resulting state |
| ACKNOWLEDGED | IN_PROGRESS or COMPLETED | Assigned target user; valid workflow evidence | User, update/completion details/time |
| IN_PROGRESS | COMPLETED | Assigned target user; completion details | User, completion details/time |

Reassignment is represented by a CANCELLED old assignment and a separate new PENDING assignment. It is not an in-place target mutation.

~~~mermaid
stateDiagram-v2
    [*] --> PENDING: authorized assignment created
    PENDING --> ACKNOWLEDGED: assigned user acknowledges
    PENDING --> UNABLE_TO_RESPOND: assigned target declines with reason
    PENDING --> CANCELLED: authorized cancellation
    PENDING --> EXPIRED: approved timeout policy only
    ACKNOWLEDGED --> IN_PROGRESS: assigned user records activity
    ACKNOWLEDGED --> COMPLETED: assigned user completes without intermediate work
    ACKNOWLEDGED --> UNABLE_TO_RESPOND: assigned target cannot continue
    ACKNOWLEDGED --> CANCELLED: authorized cancellation
    IN_PROGRESS --> COMPLETED: assigned user completes
    IN_PROGRESS --> UNABLE_TO_RESPOND: assigned target cannot continue
    IN_PROGRESS --> CANCELLED: authorized cancellation
    COMPLETED --> [*]
    UNABLE_TO_RESPOND --> [*]
    CANCELLED --> [*]
    EXPIRED --> [*]
~~~

Reassignment cancels/supersedes the old assignment and creates a new PENDING record; it never edits away prior status history. Police can update only the Police assignment; Hospital can update only the Hospital assignment. Hospital readiness is not medical treatment, and Police response is not an operational emergency response.

## Multi-Agency Response

The owner-approved Police-first path creates a post-verification request for the designated Hospital; it does not, by itself, create a Police response assignment. The general independent Police/Hospital assignment concept below remains a separate capability subject to OAD-013/OAD-018 scope and target approvals.

~~~mermaid
flowchart TD
    Incident[OPEN AccidentIncident] --> P[Police ResponseAssignment: PENDING]
    Incident --> H[Hospital ResponseAssignment: PENDING]
    P --> P1{Police action}
    H --> H1{Hospital action}
    P1 -->|acknowledge / progress / complete / unable| PH[Police-only AssignmentStatusHistory and Response]
    H1 -->|acknowledge / readiness / complete / unable| HH[Hospital-only AssignmentStatusHistory and Response]
    PH --> Aggregate[Backend incident review; independent state remains visible]
    HH --> Aggregate
    Aggregate -->|first IN_PROGRESS| Active[Incident RESPONSE_ACTIVE]
    Aggregate -->|all assignments terminal or approved override| Resolve[Authorized incident resolution]
~~~

One agency's acknowledgement, failure, inability, or completion does not alter another agency's assignment. The overall incident is not “acknowledged” by either agency. If one assignment remains nonterminal, the incident remains unresolved under the proposed default.

## Notification Lifecycle

Notification state is separate from incident and assignment state:

| State | Meaning and transition rule |
|---|---|
| CREATED | Backend created a prototype notification record |
| PENDING | Simulated in-app delivery is awaiting processing |
| DELIVERED_SIMULATED | Prototype notification was shown/recorded; not external delivery |
| READ | Recipient viewed the prototype notification; does not acknowledge assignment |
| FAILED | Simulated delivery attempt failed; incident/assignment unchanged |
| CANCELLED | Authorized cancellation of this notification only |

Retries may move FAILED to PENDING under an approved bounded simulation policy. No state sends an emergency alert.

## Assignment Non-Acknowledgement and Recovery

Proposed default: show an auditable overdue indicator and require manual follow-up by an authorized assignment actor. Do not invent a timeout interval, automatically expire assignments, or escalate externally. If a later approved timeout applies, EXPIRED is an assignment-only state and records the policy/version. Reassignment preserves the old assignment history.

## Failure and Edge-Case Matrix

| Trigger | Expected/data-consistent behavior | Audit and visible outcome | Retry/recovery and approval |
|---|---|---|---|
| Invalid AI_SERVICE credentials | Deny before creating event/candidate | Record identity and denial, never credential; safe intake error | Correct identity and retry; mechanism/rotation pending |
| Unauthorized VideoSource | Do not process or accept resulting events | Record source reference/denial; operator sees unauthorized | Source owner/admin reviews; registry authority pending |
| Duplicate event ID | Return prior intake result; do not create another event or response | Link idempotent result in history | Retry same ID; contract pending |
| Multiple events may share candidate | Preserve distinct events; uncertain match is flagged | Reviewer sees candidate/event provenance | Manual association; matching policy pending |
| Candidate rejected | Keep REJECTED candidate and audit; no incident | Reviewer reason visible within scope | Retention/reopen policy pending |
| Candidate verification failure | Candidate stays UNDER_REVIEW; no incident | Pending/error visible to reviewer | Retry/manual review; authority/SLA pending |
| Evidence upload/integrity failure | Asset FAILED/QUARANTINED; never AVAILABLE | Audit; evidence shown unavailable | Retry scoped upload or backend fallback; limits/scanning pending |
| Evidence access denied | Do not issue access or reveal storage/object existence | Audit attempt; safe denial | Request authorized assignment; scope policy pending |
| Object storage unavailable | Candidate/incident unchanged; asset unavailable | Operator/reviewer sees transfer failure | Retry/reconcile later; provider behavior pending |
| Backend unavailable during event submission | Caller assumes unknown, retries same ID; no silent loss/duplication | Audit once accepted; service pending outcome | Idempotent retry; retry window pending |
| Database transaction failure | No partial candidate/incident/history state | Safe failure and correlated operational log | Retry same decision idempotently; transaction design future |
| Police not acknowledged | Police assignment stays PENDING/overdue | Admin sees Police-only overdue indicator | Manual follow-up default; timeout policy pending |
| Hospital not acknowledged | Hospital assignment stays PENDING/overdue | Admin sees Hospital-only indicator | Manual follow-up default; timeout policy pending |
| One agency acknowledges, other pending | Update only the acknowledging assignment | Both states visible separately | Follow up only with pending target |
| Agency unable to respond | Its assignment becomes UNABLE_TO_RESPOND with reason | Actor/reason/time visible to authorized Admin | Create new assignment if approved |
| Assignment cancellation/reassignment | Old record becomes CANCELLED; new record is created separately | Preserve both histories and target attribution | Authorized assignment actor; authority pending |
| Partial response completion | One assignment can be COMPLETED while another remains active | Do not aggregate to incident completion | Resolve outstanding assignment first or approved override |
| Resolve with outstanding assignment | Deny RESOLVED while any assignment nonterminal by default | Audit attempt and show blocker | Complete/cancel/unable/approved-expire; override policy pending |
| Unauthorized closure | Deny; incident remains current/RESOLVED | Audit attempt; safe error | Authorized closer retries; authority pending |
| Duplicate incident correction | Do not silently merge/delete; preserve relation/history | Authorized reviewer sees possible duplicate | Manual correction/merge policy pending |
| Reopen request | Deny until approved policy; never overwrite CLOSED history | Record request and outcome | Team must approve actor/reason/state path |
| Notification failure | Notification FAILED; incident and assignment unchanged | Clearly simulated error state | Bounded simulation retry; no real channel |
| Missing/uncertain location | Preserve unknown, source, and uncertainty | UI distinguishes camera vs accident claim | Authorized correction with history; policy pending |
| VideoSource unavailable | No analysis or candidate; distinguish from no accident | Record source/time failure | Retry/manual source check; health policy pending |

All state transitions are backend-authorized, validated against current state, and audited. No failure or timeout handling may contact emergency services.
