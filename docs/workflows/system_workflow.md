# End-to-End System Workflow

**Status:** REVISED_DRAFT — pending team approval; internal domain services implement selected workflows, while source/provider integration interfaces and HTTP contracts are not implemented.

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
    N --> O{Specifically authorized Police reviewer decision}
    O -- Reject --> P[Candidate REJECTED; retain per policy; no incident or Hospital request]
    O -- Inconclusive --> P2[Candidate remains UNDER_REVIEW; no incident or Hospital request]
    O -- Verify --> Q[Backend transaction sets candidate VERIFIED and creates linked OPEN AccidentIncident]
    Q --> R[After commit, create incident-linked request for designated Hospital]
    R --> S[Create simulated in-app notification]
    S --> T[Hospital records acknowledgement and availability or inability]
    T --> T2[Hospital records separate simulated ambulance-dispatch decision and response status]
    T2 --> U[Authorized users track incident and Hospital response independently]
    U --> V[Resolve/close separately under approved authority]
    V --> W[Retain incident, Hospital response, evidence, location, and audit records per policy]
~~~

## Actor and System Responsibilities

| Step | Responsible party | Required behavior |
|---|---|---|
| Source registration/input | Source owner/operator and authorized registry actor | Document owner permission, source identity, processing policy, location/time provenance; allow controlled-file demos |
| Analysis and event production | AI service | Produce distinct DetectionEvents and evidence metadata; preserve source/time/model provenance and uncertainty |
| Event intake/candidate association | Backend | Authenticate AI_SERVICE, deduplicate event identity, preserve events, associate/create candidates, flag uncertain matches |
| Candidate verification | Specifically authorized human Police reviewer | Review only permitted information and record the decision under the approved policy; Police reviewer role/order is owner-approved, while individual identity/scope/criteria remain pending; AI cannot decide |
| Incident creation | Backend | Atomically create one OPEN AccidentIncident only after approved verification |
| Hospital request | Backend after incident commit | Create an incident-linked request for the designated Hospital; target routing, request/assignment mapping, and retry contract remain pending |
| Notification | Backend notification component | Maintain simulated in-app delivery/read state; never imply Hospital acknowledgement or contact an emergency organization |
| Hospital response tracking | Specifically authorized user in the designated Hospital scope | Record acknowledgement and availability/inability, then a separate simulated ambulance-dispatch decision and subsequent simulated status; exact states and permissions remain pending |
| Other agency assignments | Separately approved assignment policy | Any Police response assignment beyond candidate verification is not part of the owner-approved flow and remains subject to target/authority approval |
| Incident resolution/closure | Authorized incident-level actor (TBD) | Review assignment outcomes; resolve and close as separate, audited decisions |

## Failure, Retry, and Duplicate Paths

- Invalid AI_SERVICE identity, source permission, or payload: reject before candidate/incident mutation and audit safely.
- Duplicate event ID: return prior result; different events remain distinct and may be associated to one candidate under a reviewed policy.
- AI/model failure: report processing failure separately from no-candidate; no candidate verification or incident creation.
- Insufficient/contradictory evidence: leave candidate UNDER_REVIEW or reject through authorized human; never auto-verify.
- Verification/incident database transaction failure: commit neither falsely verified candidate nor orphan incident; retry idempotently.
- Rejected/inconclusive candidate: create no Hospital request. Hospital request creation is after incident commit and must not duplicate the incident; target/routing failures remain auditable and retryable under an approved contract.
- Hospital acknowledgement and simulated dispatch/status: treat as separate, scoped events; never infer dispatch from acknowledgement or report a simulated status as real.
- Evidence upload or integrity failure: remain FAILED/QUARANTINED and unavailable; candidate/incident state remains intact.
- Backend timeout after event submission: caller treats result as unknown and retries the same event identity.
- One agency non-acknowledgement, inability, or failure: update only its ResponseAssignment; use overdue/manual follow-up by default.
- Incident resolution with a nonterminal assignment: block under proposed policy unless approved audited override exists.
- Missing/uncertain location: preserve provenance and uncertainty; never substitute camera coordinates as exact accident location.
- Notification, map, or storage outage: retain incident state and surface provider/evidence unavailability; no live fallback.
- Out-of-scope access or stale transition: deny safely, do not expose object existence, and audit sensitive attempts.

## Boundaries

The backend is authoritative for identity, event intake, candidates, incidents, assignments/requests, notification records, evidence metadata, location provenance, and audit. PostgreSQL stores structured state and metadata; object storage holds media bytes only. Provider details, concrete API schemas, request/dispatch state mapping, Hospital routing, grouping method, thresholds, retention, timeout values, and response-time targets remain TBD. See the [Accident Verification and Emergency Response Governance Workflow](../architecture/domain/accident_verification_emergency_response_workflow.md).
