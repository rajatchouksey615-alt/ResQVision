# Use Cases

**Status:** REVISED_DRAFT — pending team approval. These use cases describe planned behavior and do not define API contracts.

## Actors

| Actor | Description |
|---|---|
| ADMIN | Prototype user administrator and incident oversight role; exact verification authority is proposed and needs approval |
| POLICE | Authorized incident reviewer and simulated response-status actor |
| HOSPITAL | Authorized incident reviewer and simulated readiness-status actor |
| AI service | Authenticated machine actor that analyzes approved video and submits DetectionEvents and associated evidence metadata for backend candidate association |
| Video source owner/operator | Provides an approved input and confirms permitted purpose and handling; source-registry authority is TBD |
| Backend system | Enforces access, owns incident records, applies transitions, and records audit history |

## UC-01 — Authenticate and access a role dashboard

- **Primary actor:** ADMIN, POLICE, or HOSPITAL.
- **Preconditions:** Account exists and is enabled; client can reach backend.
- **Main flow:** Actor submits credentials; backend authenticates; client receives authorized session; backend returns role-scoped dashboard information.
- **Alternatives/exceptions:** Invalid/disabled account is denied; service outage shows a retryable error; protected data is not cached as accessible after logout.
- **Postconditions:** Successful session is attributable; no role privilege is inferred from client navigation.
- **Related requirements:** FR-001, FR-002, FR-013.

## UC-02 — Process an authorized VideoSource input

- **Primary actor:** AI service; source owner/operator supplies the input.
- **Preconditions:** Source, purpose, and data-use permission are approved; supported processing environment is available.
- **Main flow:** Backend registry identifies an authorized VideoSource; service validates source/policy metadata; samples/preprocesses frames; detects and tracks relevant objects; applies temporal analysis; produces one or more DetectionEvents with source/time provenance.
- **Alternatives/exceptions:** Unauthorized, malformed, corrupt, or unavailable input is rejected/failed distinctly; resource exhaustion is recorded as a processing failure, not a negative detection.
- **Postconditions:** DetectionEvent or traceable processing outcome exists; event remains distinct from candidate and incident.
- **Related requirements:** FR-003, FR-004, FR-028, FR-029.

## UC-03 — Police reviews an AccidentCandidate and creates incident only on verification

- **Primary actor:** Specifically authorized human Police reviewer (role/order approved by project owner on 2026-11-19; individual identity/scope/criteria pending); AI service supplies observations only.
- **Preconditions:** Backend has accepted one or more DetectionEvents and created/associated an AccidentCandidate in RECEIVED.
- **Main flow:** Candidate enters UNDER_REVIEW; the designated Police reviewer examines only permitted event/evidence/location information and records a decision under the approved verification policy; on verification, the backend atomically creates one linked OPEN AccidentIncident, then creates an incident-linked request for the designated Hospital.
- **Alternatives/exceptions:** Candidate remains UNDER_REVIEW if inconclusive or information is insufficient/contradictory; rejected and inconclusive candidates create neither incident nor Hospital request; transaction failure creates neither false verification nor orphan incident; Hospital request failure is recoverable without duplicating the incident.
- **Postconditions:** Candidate/incident/request links, Police reviewer decision, Hospital response events, time, and audit are preserved. Hospital acknowledgement/availability and simulated dispatch/status are distinct; no real dispatch occurs.
- **Related requirements:** FR-005, FR-018, FR-019, FR-030, FR-032.

## UC-04 — Review and update one agency's ResponseAssignment

- **Primary actors:** POLICE and HOSPITAL.
- **Preconditions:** Actor is authenticated and has a ResponseAssignment for that specific agency target.
- **Main flow:** Actor reviews minimized incident summary and authorized evidence; acknowledges own PENDING assignment; records an independent Response/progress/completion/readiness update; backend validates and audits.
- **Alternatives/exceptions:** Out-of-scope, stale, or invalid transition is denied; action never mutates another agency's assignment or the incident acknowledgement state.
- **Postconditions:** AssignmentStatusHistory and Response are attributable; Hospital readiness is not a treatment claim; all prototype activity is simulated.
- **Workflow boundary:** The owner-approved Hospital request follows Police verification and incident creation. Whether that request is represented by `ResponseAssignment` or another record, and how simulated dispatch statuses map to `Response`, remains unresolved.
- **Related requirements:** FR-006, FR-011, FR-012, FR-020, FR-021, FR-023.

## UC-05 — Administer users and oversee incidents

- **Primary actor:** ADMIN.
- **Preconditions:** Admin authenticated and has the specific permission.
- **Main flow:** Admin creates/updates/disables users or roles and reviews only specifically authorized incident summaries or audit data. Candidate verification or assignment management requires a separate explicit grant; Admin role alone provides neither.
- **Alternatives/exceptions:** Invalid roles, out-of-policy action, or unauthorized evidence access is denied and recorded as appropriate.
- **Postconditions:** Changes are persisted by the backend and auditable.
- **Related requirements:** FR-002, FR-008, FR-013, FR-016.

## UC-06 — Submit a DetectionEvent to the backend

- **Primary actor:** AI service.
- **Preconditions:** AI_SERVICE identity is authenticated; approved VideoSource and stable event identity are supplied under a future contract.
- **Main flow:** Service submits one event and evidence metadata; backend validates machine identity, source authorization, and payload; backend stores event/outcome and associates it to or creates candidate; returns a safe intake result.
- **Alternatives/exceptions:** Identical event ID is idempotent; distinct possible duplicate event is preserved/flagged; invalid credential/source is denied; backend timeout is retried with same event ID.
- **Postconditions:** Provenance is retained; AI_SERVICE cannot verify, create incident, assign, respond, or administer users.
- **Related requirements:** FR-004, FR-007, FR-017, FR-018, FR-028.

## UC-07 — Record simulated notification and response

- **Primary actors:** Backend system, ADMIN, POLICE, HOSPITAL.
- **Preconditions:** A permitted incident event or assignment occurs.
- **Main flow:** Backend creates a simulated notification record; recipient sees/marks the notification READ within allowed scope; assignment acknowledgement is a separate operation on that recipient's ResponseAssignment.
- **Alternatives/exceptions:** Simulated delivery failure or retry is recorded; no real push to an emergency organization is attempted.
- **Postconditions:** Notification and assignment/response records remain separate and clearly labeled as prototype simulation.
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
- **Main flow:** System distinguishes repeated event ID, distinct related events, candidate association, processing failure, no candidate, and uncertain candidate; preserves every accepted event and its links; routes uncertain grouping/review to an authorized human.
- **Alternatives/exceptions:** If deduplication cannot be established confidently, backend records a possible duplicate for authorized review instead of discarding it.
- **Postconditions:** No failure or uncertainty is silently converted to VERIFIED; retry and audit behavior remains traceable.
- **Related requirements:** FR-003, FR-004, FR-017, FR-018, FR-030.

## UC-10 — Upload and validate an EvidenceAsset

- **Primary actor:** AI_SERVICE; backend and object storage provide the transfer boundary.
- **Preconditions:** Candidate exists; AI_SERVICE is authenticated; evidence metadata is permitted.
- **Main flow:** AI_SERVICE requests an upload authorization for one asset; backend creates a server-controlled reference and PENDING_UPLOAD metadata; backend issues short-lived object-scoped upload permission where supported; service uploads; backend verifies expected reference, type/size, and integrity; asset becomes QUARANTINED for required scanning and AVAILABLE only after success.
- **Alternatives/exceptions:** Unauthorized/expired/reused authorization is denied; failed transfer/integrity/scanning leaves asset FAILED or QUARANTINED; backend-mediated upload is the provider fallback.
- **Postconditions:** Evidence metadata and audit are stored in backend; object storage holds bytes only; asset is not retrievable until AVAILABLE.
- **Related requirements:** FR-006, FR-025, FR-026, FR-030.

## UC-11 — Retrieve an EvidenceAsset

- **Primary actor:** ADMIN, POLICE, or HOSPITAL within approved scope.
- **Preconditions:** User authenticated; asset AVAILABLE; asset is related to a candidate/incident in the user's scope.
- **Main flow:** Client requests by logical asset reference; backend checks object, role, assignment and data-minimization policy; backend streams media or provides short-lived restricted retrieval; access is audited.
- **Alternatives/exceptions:** Denied, expired, deleted, quarantined, or unavailable evidence returns safe outcome without disclosing a storage path or unrelated object existence.
- **Postconditions:** No broad object-store credentials reach mobile client; sensitive retrieval attempt is attributable.
- **Related requirements:** FR-006, FR-027, FR-030.

## UC-12 — Track independent Police and Hospital assignments

- **Primary actors:** ADMIN/approved assignment actor, POLICE, HOSPITAL, backend.
- **Preconditions:** Verified candidate has created an OPEN AccidentIncident.
- **Main flow:** Authorized actor creates separate PENDING assignment records for eligible Police and Hospital targets; each target independently acknowledges, records Response, completes, or reports inability; notification records are created separately; incident becomes RESPONSE_ACTIVE when response activity begins.
- **Alternatives/exceptions:** One target remains pending or is unable to respond; other assignment is unchanged; reassignment cancels the old assignment and creates a new one; overdue default is a manual-review indicator.
- **Postconditions:** Assignment histories and incident history are separate; no notification or one agency acknowledgement marks the entire incident acknowledged.
- **Related requirements:** FR-020, FR-021, FR-022, FR-023, FR-024, FR-031.

## UC-13 — Preserve location provenance

- **Primary actors:** VideoSource owner/operator, AI_SERVICE, authorized human reviewer, backend.
- **Preconditions:** A location claim comes from registered camera location, approved GPS metadata, inferred estimate, or human verification.
- **Main flow:** Backend records origin/source/time/uncertainty and links claim to the relevant VideoSource, event, candidate, or incident; authorized client shows the claim and its uncertainty; a permitted manual correction appends history.
- **Alternatives/exceptions:** Missing, conflicting, or imprecise location remains unknown/uncertain; camera coordinates are never silently labeled accident coordinates.
- **Postconditions:** Provenance and corrections are auditable and access-scoped.
- **Related requirements:** FR-010, FR-029.
