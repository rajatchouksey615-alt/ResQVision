# Use Cases

**Status:** Draft for team review. These use cases describe planned behavior and do not define API contracts.

## Actors

| Actor | Description |
|---|---|
| ADMIN | Prototype user administrator and incident oversight role; exact verification authority is proposed and needs approval |
| POLICE | Authorized incident reviewer and simulated response-status actor |
| HOSPITAL | Authorized incident reviewer and simulated readiness-status actor |
| AI service | Authenticated machine actor that analyzes approved video and submits candidate evidence |
| Video source owner/operator | Provides an approved input and confirms permitted purpose and handling |
| Backend system | Enforces access, owns incident records, applies transitions, and records audit history |

## UC-01 — Authenticate and access a role dashboard

- **Primary actor:** ADMIN, POLICE, or HOSPITAL.
- **Preconditions:** Account exists and is enabled; client can reach backend.
- **Main flow:** Actor submits credentials; backend authenticates; client receives authorized session; backend returns role-scoped dashboard information.
- **Alternatives/exceptions:** Invalid/disabled account is denied; service outage shows a retryable error; protected data is not cached as accessible after logout.
- **Postconditions:** Successful session is attributable; no role privilege is inferred from client navigation.
- **Related requirements:** FR-001, FR-002, FR-013.

## UC-02 — Process an approved video input

- **Primary actor:** AI service; source owner/operator supplies the input.
- **Preconditions:** Source, purpose, and data-use permission are approved; supported processing environment is available.
- **Main flow:** Service validates input and permission metadata; samples/preprocesses frames; detects and tracks relevant objects; applies temporal analysis; produces a candidate or a no-candidate outcome with provenance.
- **Alternatives/exceptions:** Unauthorized, malformed, corrupt, or unavailable input is rejected/failed distinctly; resource exhaustion is recorded as a processing failure, not a negative detection.
- **Postconditions:** Candidate evidence or a traceable processing outcome exists; no candidate is represented as a confirmed accident.
- **Related requirements:** FR-003, FR-004.

## UC-03 — Verify a candidate

- **Primary actor:** Authorized reviewer (role TBD; ADMIN is a proposal); AI service supplies evidence.
- **Preconditions:** Candidate is DETECTED and backend has accepted its provenance.
- **Main flow:** Backend places candidate UNDER_VERIFICATION; reviewer examines temporal evidence and uncertainty; reviewer records verified or rejected decision with rationale; backend applies an allowed transition and audits it.
- **Alternatives/exceptions:** Evidence is insufficient, contradictory, unavailable, or review is delayed; candidate remains pending or is rejected according to an approved rule.
- **Postconditions:** Decision and actor/time are auditable; only VERIFIED candidates can proceed to assignment.
- **Related requirements:** FR-005, FR-016.

## UC-04 — Review and update an assigned incident

- **Primary actors:** POLICE and HOSPITAL.
- **Preconditions:** Actor is authenticated and incident is assigned within the actor's authorized scope.
- **Main flow:** Actor reviews the permitted summary and evidence; acknowledges the assignment; records permitted response/readiness updates; the backend validates and audits each transition.
- **Alternatives/exceptions:** Out-of-scope incident, stale state, or invalid transition is denied; media or map unavailability does not fabricate information.
- **Postconditions:** Response status and attribution are available to authorized users.
- **Related requirements:** FR-006, FR-011, FR-012, FR-014.

## UC-05 — Administer users and oversee incidents

- **Primary actor:** ADMIN.
- **Preconditions:** Admin authenticated and has the specific permission.
- **Main flow:** Admin creates/updates/disables users or roles, reviews authorized incident summaries, performs approved verification/assignment actions, and inspects audit history.
- **Alternatives/exceptions:** Invalid roles, out-of-policy action, or unauthorized evidence access is denied and recorded as appropriate.
- **Postconditions:** Changes are persisted by the backend and auditable.
- **Related requirements:** FR-002, FR-008, FR-013, FR-016.

## UC-06 — Submit a detection event to the backend

- **Primary actor:** AI service.
- **Preconditions:** Service identity is authenticated; event format and retry/idempotency rules have been agreed for implementation.
- **Main flow:** Service submits candidate provenance and evidence references; backend validates source and service identity; backend creates or links the candidate; backend returns a safe accepted/rejected outcome.
- **Alternatives/exceptions:** Repeated event is recognized or safely flagged for review; invalid signature/identity, malformed payload, or unavailable backend does not silently lose the event.
- **Postconditions:** Backend remains the single source of truth; service cannot set response states or dispatch responders.
- **Related requirements:** FR-004, FR-007, FR-016.

## UC-07 — Record simulated notification and response

- **Primary actors:** Backend system, ADMIN, POLICE, HOSPITAL.
- **Preconditions:** A permitted incident event or assignment occurs.
- **Main flow:** Backend creates a simulated notification record; recipient sees it within allowed scope; actor acknowledges and records status through the client.
- **Alternatives/exceptions:** Simulated delivery failure or retry is recorded; no real push to an emergency organization is attempted.
- **Postconditions:** Notification and response records are clearly labeled as prototype simulation.
- **Related requirements:** FR-009, FR-011, FR-012.

## UC-08 — Inspect history and aggregate reports

- **Primary actor:** ADMIN; scoped history is also available to POLICE and HOSPITAL.
- **Preconditions:** Actor is authenticated and permitted to view the requested incident or aggregate.
- **Main flow:** Backend returns scoped immutable history or documented aggregate metrics; interface shows source period and limitations.
- **Alternatives/exceptions:** Insufficient data is labeled unavailable; unauthorized records are omitted or denied.
- **Postconditions:** Review is read-only except through separately authorized lifecycle actions.
- **Related requirements:** FR-014, FR-015, FR-016.

## UC-09 — Handle duplicate, failed, or uncertain analysis

- **Primary actor:** Backend system and AI service.
- **Preconditions:** An event is repeated, processing is incomplete, or evidence is uncertain.
- **Main flow:** System distinguishes duplicate candidate, processing failure, no candidate, and uncertain candidate; preserves references to related events; routes unresolved candidates to review.
- **Alternatives/exceptions:** If deduplication cannot be established confidently, backend records a possible duplicate for authorized review instead of discarding it.
- **Postconditions:** No failure or uncertainty is silently converted to VERIFIED; retry and audit behavior remains traceable.
- **Related requirements:** FR-003, FR-004, FR-007, FR-016.
