# Incident Lifecycle Policy

**Decision status:** Current lifecycle mechanics are implemented; authority and operational policy remain proposed/unresolved.  
**Related existing decisions:** OAD-012, OAD-013, OAD-018, OAD-021.  
**Related requirements:** FR-008, FR-011, FR-012, FR-020 through FR-023, FR-031; NFR-002, NFR-008 through NFR-010, NFR-020, NFR-025.

## State Ownership

An `AccidentIncident` is created only when a candidate is verified. It owns incident lifecycle state and `IncidentStatusHistory`. A `ResponseAssignment` owns one target organization's acknowledgement, progress, inability, cancellation, or completion state and `AssignmentStatusHistory`. `Response` records activity, not a second current status. Notification delivery/read is a separate simulation lifecycle.

## Incident Transition Table

| From | To | Trigger/preconditions | Actor authority | Audit/concurrency | Current status |
|---|---|---|---|---|---|
| None | `OPEN` | Authorized human verifies an `UNDER_REVIEW` candidate with event provenance; incident, candidate decision, history, and audit commit atomically. | Human verifier under OAD-012; not yet approved. AI is prohibited. | Candidate row lock, one final review, unique incident-per-candidate, command ID. | Implemented in domain service; HTTP candidate review remains blocked. |
| `OPEN` | `RESPONSE_ACTIVE` | First associated assignment transitions to `IN_PROGRESS`; acknowledgement alone is insufficient. | Backend consequence of a scoped Police/Hospital assignment command. | Same transaction as assignment/status history and audit; incident lock serializes concurrent starts. | Implemented. |
| `OPEN` | `RESOLVED` | Incident-level resolve command; nonblank reason; all assignments in current terminal set. | Designated resolver; exact role/scope unresolved. | Incident and assignments locked; command ID prevents duplicate/conflicting transition. | Service exists; API returns 503. |
| `RESPONSE_ACTIVE` | `RESOLVED` | Same as above. | Designated resolver; exact role/scope unresolved. | Same as above. | Service exists; API returns 503. |
| `RESOLVED` | `CLOSED` | Separate close command with nonblank reason. | Designated closer; whether separate from resolver is unresolved. | Incident lock; transition history and audit in transaction; command ID. | Service exists; API returns 503. |
| `CLOSED` | `OPEN` or other | No current transition. | None. | Any future reopening needs explicit command, reason, audit, idempotency, and schema/service review. | Not implemented; recommend denied by default. |
| Any | `CANCELLED`/`INVALID` | No incident-level cancelled/invalid state exists. | None. | Do not infer candidate rejection after an incident exists. Define correction/invalidity semantics first. | Not implemented/unresolved. |

~~~mermaid
stateDiagram-v2
    [*] --> OPEN: candidate verified by authorized human
    OPEN --> RESPONSE_ACTIVE: first assignment enters IN_PROGRESS
    OPEN --> RESOLVED: authorized resolver; all assignments terminal
    RESPONSE_ACTIVE --> RESOLVED: authorized resolver; all assignments terminal
    RESOLVED --> CLOSED: authorized closer and reason
    CLOSED --> [*]
~~~

The model has no status for an incident awaiting assignment. `OPEN` therefore includes the time before any assignment is created.

## Resolution Preconditions and Current Terminal Rule

The current service accepts only `COMPLETED`, `UNABLE_TO_RESPOND`, and `CANCELLED` assignments as terminal for resolution. `EXPIRED` exists in the assignment status vocabulary but has no transition implementation, no expiry worker/route, and is not accepted by the resolver. Do not count it as terminal unless OAD-021 is decided and the transition, timeout source, audit, and retry behavior are implemented.

No override path exists. The role matrix/workflow mentions a possible separately approved override, but code requires all assignments terminal. The recommendation is to keep this strict guard for the MVP and approve any override only with named scope, mandatory reason, recorded outstanding assignments, and separate audit. The draft workflow proposes an `OPEN → RESOLVED` no-response outcome. The current service also permits resolution with zero assignments because its all-terminal check passes for an empty set; it requires a general nonblank reason but does not require that the reason identify a no-response outcome. Confirm this behavior explicitly before enabling the endpoint.

## Actor-to-Transition Recommendation

| Actor | Read incident | Update incident lifecycle | Update assignment | Recommendation / boundary |
|---|---|---|---|---|
| ADMIN | Only through currently authorized membership/assignment scope; no global bypass. | No blanket grant. A specifically designated incident authority may resolve/close if approved. | Cannot update target agency work by role alone; any assignment administration requires a separate permission. | Existing draft says Admin oversight is proposed; exact authority remains unresolved. |
| POLICE | Only an incident with an active matching Police membership and visible Police assignment. | No incident resolve/close permission by default. | Own authorized Police-target assignment only. | Membership and target scope are enforced by current services/selectors. |
| HOSPITAL | Only an incident with an active matching Hospital membership and visible Hospital assignment; minimum necessary fields. | No incident resolve/close permission by default. | Own authorized Hospital-target assignment only; readiness is simulated. | Membership and target scope are enforced by current services/selectors. |
| AI_SERVICE | No human incident workspace. | No incident transition permission. | No assignment permission. | Machine identity stays separate; current authenticator is not configured. |

These are recommendations, not approved grants. Every route that invokes an unresolved lifecycle operation must continue to fail closed.

## Independent Agency Assignment Lifecycle

Current assignment transitions in `backend/apps/responses/services/assignments.py` are:

~~~mermaid
stateDiagram-v2
    [*] --> PENDING: approved assignment creation
    PENDING --> ACKNOWLEDGED: target member acknowledges
    PENDING --> UNABLE_TO_RESPOND: target member with reason
    PENDING --> CANCELLED: separately authorized cancellation
    ACKNOWLEDGED --> IN_PROGRESS: target records progress/readiness
    ACKNOWLEDGED --> COMPLETED: target completes
    ACKNOWLEDGED --> UNABLE_TO_RESPOND: target member with reason
    ACKNOWLEDGED --> CANCELLED: separately authorized cancellation
    IN_PROGRESS --> COMPLETED: target completes
    IN_PROGRESS --> UNABLE_TO_RESPOND: target member with reason
    IN_PROGRESS --> CANCELLED: separately authorized cancellation
    PENDING --> EXPIRED: only after OAD-021 approval and implementation
    COMPLETED --> [*]
    UNABLE_TO_RESPOND --> [*]
    CANCELLED --> [*]
    EXPIRED --> [*]
~~~

`EXPIRED` is a schema state only today. Reassignment is represented in the domain service as a cancelled prior assignment plus a new linked assignment, but both reassignment and assignment creation authority remain policy-blocked. No assignment-creation endpoint is exposed. No automatic escalation follows non-acknowledgement.

Agency completion does not automatically resolve or close the incident. It only makes that assignment terminal. Incident closure requires a separate incident-level decision after resolution.

## Audit, Idempotency, and Error Behavior

Record prior/resulting status, actor, UTC time, reason where required, target organization, related incident/assignment, and command ID. A nonblank resolution and closure reason is mandatory in the service. Keep each transition's audit and history in the same transaction as state. Invalid or stale commands must not change state; record safe denial metadata outside the rolled-back business transaction. Use a 503 policy-unavailable response for unresolved commands; scoped out-of-resource reads remain 404.

## Approval Questions

Approve the resolver/closer role and scope; whether resolver and closer are separate duties; whether zero-assignment resolution is allowed; whether to allow an override and its audit fields; whether reopening or invalidating an incident is ever needed; exact non-acknowledgement policy; and whether `EXPIRED` can satisfy the resolution guard. Until then, no lifecycle route should be enabled.
