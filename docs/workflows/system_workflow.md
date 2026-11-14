# End-to-End System Workflow

**Status:** REVISED_DRAFT — pending team approval; source interfaces and service contracts are not implemented.

~~~mermaid
flowchart TD
    A[Register/configure VideoSource] --> B{Ownership and processing authorization valid?}
    B -- No --> X[Reject input; audit; no DetectionEvent accepted]
    B -- Yes --> C[AI validates source, processes input, preserves time/location provenance]
    C --> D{Detection observations?}
    D -- No --> E[Record processing outcome; no candidate]
    D -- Yes --> F[Submit authenticated DetectionEvent(s)]
    F --> G{AI_SERVICE, source, payload, event identity valid?}
    G -- No --> H[Reject safely; retry only with same event identity]
    G -- Yes --> I[Backend stores each distinct DetectionEvent]
    I --> J{Existing AccidentCandidate confidently related?}
    J -- Yes --> K[Associate event; preserve provenance]
    J -- No --> L[Create AccidentCandidate RECEIVED]
    J -- Uncertain --> M[Flag possible duplicate for authorized review]
    K --> N[Candidate UNDER_REVIEW]
    L --> N
    M --> N
    N --> O{Authorized human decision}
    O -- Reject --> P[Candidate REJECTED; retain per policy; no incident]
    O -- Verify --> Q[Backend transaction sets candidate VERIFIED and creates linked OPEN AccidentIncident]
    Q --> R[Create separate Police/Hospital ResponseAssignments]
    R --> S[Create separate simulated Notifications]
    S --> T[Each assigned agency updates only its own assignment and Response history]
    T --> U[Incident RESPONSE_ACTIVE when response work starts]
    U --> V[Resolve after assignment outcomes; close separately under approved authority]
    V --> W[Retain incident, assignment, evidence, location, and audit records per policy]
~~~

## Actor and System Responsibilities

| Step | Responsible party | Required behavior |
|---|---|---|
| Source registration/input | Source owner/operator and authorized registry actor | Document owner permission, source identity, processing policy, location/time provenance; allow controlled-file demos |
| Analysis and event production | AI service | Produce distinct DetectionEvents and evidence metadata; preserve source/time/model provenance and uncertainty |
| Event intake/candidate association | Backend | Authenticate AI_SERVICE, deduplicate event identity, preserve events, associate/create candidates, flag uncertain matches |
| Candidate verification | Authorized human reviewer (role TBD; Admin proposed) | Review evidence and record VERIFIED/REJECTED with rationale; AI cannot decide |
| Incident creation | Backend | Atomically create one OPEN AccidentIncident only after approved verification |
| Assignment | Admin/approved assignment policy | Create separate assignment per Police/Hospital target |
| Notification | Backend notification component | Maintain separate simulated delivery/read state; never imply acknowledgement or contact emergency organization |
| Response tracking | Each POLICE/HOSPITAL target | Update only its own assignment and Response history; simulate actions |
| Incident resolution/closure | Authorized incident-level actor (TBD) | Review assignment outcomes; resolve and close as separate, audited decisions |

## Failure, Retry, and Duplicate Paths

- Invalid AI_SERVICE identity, source permission, or payload: reject before candidate/incident mutation and audit safely.
- Duplicate event ID: return prior result; different events remain distinct and may be associated to one candidate under a reviewed policy.
- AI/model failure: report processing failure separately from no-candidate; no candidate verification or incident creation.
- Insufficient/contradictory evidence: leave candidate UNDER_REVIEW or reject through authorized human; never auto-verify.
- Verification/incident database transaction failure: commit neither falsely verified candidate nor orphan incident; retry idempotently.
- Evidence upload or integrity failure: remain FAILED/QUARANTINED and unavailable; candidate/incident state remains intact.
- Backend timeout after event submission: caller treats result as unknown and retries the same event identity.
- One agency non-acknowledgement, inability, or failure: update only its ResponseAssignment; use overdue/manual follow-up by default.
- Incident resolution with a nonterminal assignment: block under proposed policy unless approved audited override exists.
- Missing/uncertain location: preserve provenance and uncertainty; never substitute camera coordinates as exact accident location.
- Notification, map, or storage outage: retain incident state and surface provider/evidence unavailability; no live fallback.
- Out-of-scope access or stale transition: deny safely, do not expose object existence, and audit sensitive attempts.

## Boundaries

The backend is authoritative for identity, event intake, candidates, incidents, assignments, notification records, evidence metadata, location provenance, and audit. PostgreSQL stores structured state and metadata; object storage holds media bytes only. Provider details, concrete API schemas, grouping method, thresholds, retention, timeout values, and response-time targets remain TBD.
