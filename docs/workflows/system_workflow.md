# End-to-End System Workflow

**Status:** Proposed workflow for team review; source interfaces are not implemented.

~~~mermaid
flowchart TD
    A[Approved video input] --> B{Source and format permitted?}
    B -- No --> X[Reject and audit processing failure]
    B -- Yes --> C[AI preprocesses, detects, tracks, analyzes time]
    C --> D{Candidate evidence sufficient?}
    D -- No candidate --> E[Record no-candidate or uncertain outcome]
    D -- Candidate --> F[Submit authenticated candidate and evidence reference]
    F --> G{Backend identity, payload, duplicate checks pass?}
    G -- No --> H[Reject or flag possible duplicate; safe retry outcome]
    G -- Yes --> I[Record DETECTED, then UNDER_VERIFICATION]
    I --> J[Authorized human review under approved policy]
    J --> K{Verified?}
    K -- No --> L[REJECTED or remain pending; audit rationale]
    K -- Yes --> M[VERIFIED]
    M --> N[Assign eligible responder group]
    N --> O[Create simulated notification]
    O --> P[POLICE/HOSPITAL acknowledge and update]
    P --> Q[Resolve and close under approved authority]
    Q --> R[Retain incident/audit per approved policy]
~~~

## Actor and System Responsibilities

| Step | Responsible party | Required behavior |
|---|---|---|
| Source approval and input | Source owner/operator | Supply only authorized data and purpose metadata |
| Analysis and candidate | AI service | Validate input, preserve uncertainty, report failure distinctly, submit evidence reference |
| Event intake and record | Backend | Authenticate service, validate event, detect/link duplicates where possible, persist authoritative state |
| Verification | Authorized human reviewer (role TBD; Admin proposed) | Review evidence and record verified/rejected/pending decision with rationale |
| Assignment | Admin or approved assignment policy | Assign only VERIFIED incidents to an eligible scope |
| Notification | Backend notification component | Record simulated outcome only; never contact an emergency organization |
| Response tracking | POLICE and HOSPITAL | Acknowledge in-scope assignment and record role-permitted simulated status |
| Closure and audit | Authorized human role (TBD) and backend | Apply valid transition and retain attributable history |

## Failure, Retry, and Duplicate Paths

- Invalid or unauthorized source: stop processing, record safe reason, do not create an incident.
- AI/model failure: report processing failure separately from no-candidate; no verification transition.
- Insufficient or contradictory evidence: keep pending or reject per approved policy; never silently verify.
- Backend unavailable after submission: retry under a future idempotency contract; client/service must not assume persistence from a timeout.
- Duplicate event: link to an existing candidate or flag for review when uncertain; do not trigger duplicate response work.
- Evidence, map, or notification simulation unavailable: preserve the incident and make unavailable status visible.
- Invalid role, out-of-scope access, or stale state: deny action and avoid leaking protected incident details.

## Boundaries

The backend is authoritative for identity, permission, incident state, assignment, and audit. The database stores structured state and evidence metadata; media uses future restricted object storage. Provider details, concrete API schemas, thresholds, retention, and response-time targets remain TBD.
