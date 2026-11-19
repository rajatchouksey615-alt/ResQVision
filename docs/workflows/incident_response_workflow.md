# Incident Response Workflow

**Status:** REVISED_DRAFT — pending team approval; logical workflow sequence is project-owner-approved on 2026-11-19, while detailed scopes and backend contracts remain pending.

## Candidate Lifecycle

| State | Meaning | Allowed transition and actor |
|---|---|---|
| RECEIVED | Backend accepted/associated one or more authenticated DetectionEvents with a candidate | Backend moves to UNDER_REVIEW after intake/provenance checks |
| UNDER_REVIEW | Authorized human review is pending or in progress | Specifically authorized human Police reviewer moves to VERIFIED or REJECTED; identity/scope/criteria remain pending |
| VERIFIED | Approved Police human verification policy is satisfied | Backend transaction creates one linked OPEN AccidentIncident; no direct AI transition; post-commit Hospital request follows |
| REJECTED | Human reviewer rejected the candidate | Terminal for ordinary workflow; retain per approved audit/evaluation policy |

AI temporal analysis is evidence, not authority. An AI_SERVICE cannot verify/reject a candidate. The project owner approved Police-first human verification; only specifically authorized Police reviewers may decide, not every POLICE user. Multiple DetectionEvents may support one candidate; duplicate event identity is handled idempotently, while distinct-event candidate matching is a separate policy. See the [Accident Verification and Emergency Response Governance Workflow](../architecture/domain/accident_verification_emergency_response_workflow.md) for approved scope and remaining decisions.

~~~mermaid
stateDiagram-v2
    [*] --> RECEIVED: backend accepts valid DetectionEvent association
    RECEIVED --> UNDER_REVIEW: candidate queued for human review
    UNDER_REVIEW --> VERIFIED: authorized human approves
    UNDER_REVIEW --> REJECTED: authorized human rejects
    VERIFIED --> [*]: linked OPEN AccidentIncident created
    REJECTED --> [*]: retained for audit/evaluation policy
~~~

### Candidate Transition Table

| From | To | Actor/guard | Required audit |
|---|---|---|---|
| No candidate | RECEIVED | Backend after accepting/associating a valid DetectionEvent | Event IDs, source/time provenance, intake result |
| RECEIVED | UNDER_REVIEW | Backend queues a candidate with required evidence/provenance | Queue transition and actor/service |
| UNDER_REVIEW | VERIFIED | Authorized human reviewer only; authority/criteria pending approval | Reviewer, decision, time, evidence references, rationale |
| UNDER_REVIEW | REJECTED | Authorized human reviewer only | Reviewer, decision, time, rationale |

No direct transition from RECEIVED to VERIFIED/REJECTED or from REJECTED back to active review is allowed in the proposed model. Corrections/reopening require a separately approved audited policy.

## Candidate Verification and Incident Creation

~~~mermaid
sequenceDiagram
    participant AI as AI_SERVICE
    participant API as Backend
    participant DB as PostgreSQL
    actor Reviewer as Specifically authorized Police reviewer
    AI->>API: Submit DetectionEvent(s) and evidence references
    API->>API: Authenticate machine identity, validate source/provenance, deduplicate event ID
    API->>DB: Persist each distinct DetectionEvent and create/associate AccidentCandidate
    API->>DB: Set candidate UNDER_REVIEW
    Reviewer->>API: Verify or reject with rationale
    API->>API: Check reviewer authorization and candidate state
    alt Rejected
        API->>DB: Record REJECTED and audit; do not create incident
    else Verified
        API->>DB: Atomic commit: VERIFIED candidate + linked OPEN AccidentIncident + histories/audit
        API->>DB: After incident commit, create linked request for designated Hospital
    end
~~~

If the verification/incident transaction fails, neither a falsely VERIFIED candidate nor an orphan incident is committed. Retrying the same decision must not create a second incident. An inconclusive review remains `UNDER_REVIEW` and creates neither an incident nor a Hospital request. Hospital target routing and request retry/state contracts remain open.

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
