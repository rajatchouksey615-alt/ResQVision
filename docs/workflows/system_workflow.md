# End-to-End System Workflow

**Status:** REVISED_DRAFT — pending team approval; internal domain services implement selected workflows, while source/provider integration interfaces and HTTP contracts are not implemented.

The 2026-11-21 project-owner approval sets the candidate access, assignment, outcome, incident, and audit policy. The candidate assignment mechanism and intake controls are unresolved, so the approved flow below remains unavailable in runtime. Candidate review ends at the verified incident; Hospital request/notification and simulated dispatch follow a separately governed workflow.

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
    I --> J{Approved candidate materialization trigger and authorization configured?}
    J -- No --> J0[Keep DetectionEvent as observation; no candidate]
    J -- Yes --> K[Apply approved event-to-candidate association rule]
    K --> L[Create or associate AccidentCandidate]
    L --> M[Authorized authority within relevant Police organization assigns candidate]
    M --> N[Assigned reviewer with active Police membership accesses candidate]
    N --> O{Human Police reviewer decision}
    O -- REJECTED --> P[Candidate REJECTED; no AccidentIncident]
    O -- FURTHER_REVIEW --> P2[Record outcome; preserve candidate for subsequent review; no incident]
    O -- VERIFIED --> Q[Backend transaction records VERIFIED and creates exactly one linked OPEN AccidentIncident]
    Q --> Q0[Candidate review complete]
    Q0 -. Separate Hospital workflow .-> R[Create incident-linked Hospital request after remaining decisions]
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
| Event intake/candidate association | Backend | Authenticate AI_SERVICE and authorize the source; materialize candidates only through an approved trigger/association policy. AI authentication and candidate-intake protection remain unresolved. |
| Candidate assignment | Explicitly authorized authority within the relevant Police organization | Assign candidate/reviewer within that organization; current backend permission/mechanism and candidate binding remain unresolved. |
| Candidate review/decision | Specifically assigned and authorized human Police reviewer with active membership in the candidate's assigned Police organization | Review only the assigned candidate. Record `VERIFIED`, `REJECTED`, or `FURTHER_REVIEW`; no whole-group access, global Admin bypass, or new role. AI cannot decide. |
| Incident creation | Backend | Atomically create exactly one linked `OPEN` AccidentIncident only after `VERIFIED`; create none for `REJECTED` or `FURTHER_REVIEW`. |
| Candidate audit | Backend | Trace candidate assignment, review, decisions, and incident creation using safe attributable audit records. |
| Hospital request | Backend after incident commit | Create an incident-linked request for the designated Hospital; target routing, request/assignment mapping, and retry contract remain pending |
| Notification | Backend notification component | Maintain simulated in-app delivery/read state; never imply Hospital acknowledgement or contact an emergency organization |
| Hospital response tracking | Specifically authorized user in the designated Hospital scope | Record acknowledgement and availability/inability, then a separate simulated ambulance-dispatch decision and subsequent simulated status; exact states and permissions remain pending |
| Other agency assignments | Separately approved assignment policy | Any Police response assignment beyond candidate verification is not part of the owner-approved flow and remains subject to target/authority approval |
| Incident resolution/closure | Authorized incident-level actor (TBD) | Review assignment outcomes; resolve and close as separate, audited decisions |

## Failure, Retry, and Duplicate Paths

- Invalid AI_SERVICE identity, source permission, or payload: reject before candidate/incident mutation and audit safely.
- Duplicate event ID: return prior result; this does not resolve unauthorized candidate materialization or grouping of different events.
- AI/model failure: report processing failure separately from no-candidate; no candidate verification or incident creation.
- `FURTHER_REVIEW`: record the approved outcome, create no incident, and preserve candidate for subsequent review. The model/service currently cannot record it.
- AI detection: never independently establishes an accident; only the assigned authorized Police reviewer can decide.
- Verification/incident database transaction failure: commit neither falsely verified candidate nor orphan incident; retry idempotently.
- Rejected/further-review candidate: create no incident or Hospital request. Hospital request creation follows incident commit only under its separate governance decisions.
- Hospital acknowledgement and simulated dispatch/status: treat as separate, scoped events; never infer dispatch from acknowledgement or report a simulated status as real.
- Evidence upload or integrity failure: remain FAILED/QUARANTINED and unavailable; candidate/incident state remains intact.
- Backend timeout after event submission: caller treats result as unknown and retries the same event identity.
- One agency non-acknowledgement, inability, or failure: update only its ResponseAssignment; use overdue/manual follow-up by default.
- Incident resolution with a nonterminal assignment: block under proposed policy unless approved audited override exists.
- Missing/uncertain location: preserve provenance and uncertainty; never substitute camera coordinates as exact accident location.
- Notification, map, or storage outage: retain incident state and surface provider/evidence unavailability; no live fallback.
- Out-of-scope access or stale transition: deny safely, do not expose object existence, and audit sensitive attempts.

## Boundaries

The backend is authoritative for identity, event intake, candidates, incidents, assignments/requests, notification records, evidence metadata, location provenance, and audit. PostgreSQL stores structured state and metadata; object storage holds media bytes only. Candidate assignment authority, candidate/org binding, event-to-candidate materialization, AI authentication, `FURTHER_REVIEW` implementation, permitted fields, Hospital routing, request/dispatch mapping, and retention remain open or unimplemented. See the [candidate review policy](../architecture/domain/candidate_review_verification_policy.md), [candidate review readiness](../architecture/domain/implementation_readiness.md), and [Accident Verification and Emergency Response Governance Workflow](../architecture/domain/accident_verification_emergency_response_workflow.md).
