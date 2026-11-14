# Incident Response Workflow

**Status:** Proposed lifecycle for team review. This is not an implemented backend contract.

## Proposed States

| State | Meaning |
|---|---|
| DETECTED | Backend accepted a candidate submission; no verification decision has been made |
| UNDER_VERIFICATION | Candidate is being assessed using temporal evidence and authorized human review |
| VERIFIED | Authorized verification policy was satisfied and an incident may be assigned; this does not assert operational emergency-service confirmation |
| REJECTED | Candidate was reviewed and rejected; it cannot be assigned for response |
| ASSIGNED | A verified incident has been assigned to an eligible prototype response group |
| ACKNOWLEDGED | Assigned Police or Hospital user acknowledged the simulated assignment |
| RESPONSE_IN_PROGRESS | A scoped user recorded a simulated response/readiness action |
| RESOLVED | Authorized responder reports the prototype response as resolved |
| CLOSED | Authorized closure actor completed review and closed the record |

## Proposed Transition Table

| From | To | Actor and permission | Required record |
|---|---|---|---|
| DETECTED | UNDER_VERIFICATION | Backend on accepted candidate | Candidate provenance and intake audit |
| UNDER_VERIFICATION | VERIFIED | Authorized human reviewer; role and criteria TBD, Admin proposed | Decision, actor, time, evidence references, rationale |
| UNDER_VERIFICATION | REJECTED | Authorized human reviewer; role TBD | Decision, actor, time, rationale |
| VERIFIED | ASSIGNED | Admin or approved assignment policy; Admin proposed | Eligible target, actor/policy, time |
| ASSIGNED | ACKNOWLEDGED | Assigned POLICE or HOSPITAL user | Actor, assignment reference, time |
| ACKNOWLEDGED | RESPONSE_IN_PROGRESS | Assigned POLICE or HOSPITAL user within permitted action | Update type, actor, time |
| RESPONSE_IN_PROGRESS | RESOLVED | Authorized responder; Police proposed for operational resolution, details TBD | Resolution summary and actor/time |
| RESOLVED | CLOSED | Authorized Admin or designated reviewer; approval TBD | Closure reason and actor/time |

Invalid transitions are rejected by the backend and should produce an auditable outcome. The AI service may submit observations but cannot directly set VERIFIED, ASSIGNED, ACKNOWLEDGED, RESPONSE_IN_PROGRESS, RESOLVED, or CLOSED.

## Lifecycle Diagram

~~~mermaid
stateDiagram-v2
    [*] --> DETECTED: backend accepts candidate
    DETECTED --> UNDER_VERIFICATION: intake validation
    UNDER_VERIFICATION --> VERIFIED: authorized human approves
    UNDER_VERIFICATION --> REJECTED: authorized human rejects
    VERIFIED --> ASSIGNED: authorized assignment
    ASSIGNED --> ACKNOWLEDGED: assigned responder acknowledges
    ACKNOWLEDGED --> RESPONSE_IN_PROGRESS: scoped status update
    RESPONSE_IN_PROGRESS --> RESOLVED: authorized responder resolves
    RESOLVED --> CLOSED: authorized closure
    REJECTED --> [*]
    CLOSED --> [*]
~~~

## Duplicate Events and Reopening

- Repeated submissions with a recognized event identity should be linked to the original candidate and processed idempotently.
- If duplicate confidence is uncertain, flag for authorized review rather than silently discarding or assigning a second response.
- Reopening, correction after closure, merging duplicate incidents, and appeal paths are TBD. Until approved, treat REJECTED and CLOSED as terminal for ordinary workflow actions and preserve corrections as auditable events.

## Notification and Safety

Assignment, acknowledgement, and status updates may create simulated in-app or stored notification records. No real alert is sent to Police/Hospital organizations, no ambulance is dispatched, and no external emergency integration is enabled. All demo screens and reports must label response behavior as simulated.
