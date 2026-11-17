# Testing Strategy

**Status:** REVISED_DRAFT — pending team approval. The Phase 3 PostgreSQL suite and Phase 4 API integration tests are executable; the latest PostgreSQL-backed run passed all 87 tests.

Use test-driven development for feature work: define expected behavior, write a focused failing test, implement the smallest change, and run relevant checks. Review tests and behavior together.

The Phase 4 API tests cover email login, refresh rotation/blacklisting, logout ownership, password token revocation, actor separation, organization and assignment scope, fail-closed operations, notification ownership, pagination/filter limits, request IDs, body size, and throttling. See [API test results](../api_documentation/api_testing_results.md) for the latest database availability and check results.

## Test Levels

- Unit: isolated domain rules, utility behavior, verification logic, and widgets.
- Integration: interactions with databases, storage adapters, service contracts, and external boundaries using controlled test doubles where appropriate.
- API: validation, authentication, authorization, response schemas, and error behavior.
- UI and workflow: key mobile widget and integration flows.
- AI evaluation: approved, documented datasets and metrics for false positives, false negatives, and verification behavior.

## Required Architecture Scenarios

### Detection, Candidate, and Incident

- Accept an authenticated DetectionEvent and associate it to a candidate.
- Repeating an event identity is idempotent and does not create another event, candidate, incident, or assignment.
- Multiple distinct events can support one AccidentCandidate without losing individual provenance.
- Uncertain candidate association is flagged for human review rather than silently merged.
- Invalid AI_SERVICE credentials, replayed/forged events, unauthorized/revoked VideoSources, invalid payloads, and event flooding are denied safely.
- AI_SERVICE cannot verify/reject, create an AccidentIncident, assign targets, or alter response state.
- Human verification and linked OPEN incident creation are atomic; transaction failure leaves neither a false VERIFIED candidate nor an orphan incident.
- Rejected candidates remain distinct and audited and create no AccidentIncident.

### Independent Incident and Agency Assignment Lifecycles

- Incident OPEN/RESPONSE_ACTIVE/RESOLVED/CLOSED transitions are tested separately from each assignment.
- Police and Hospital assignments have independent PENDING/ACKNOWLEDGED/IN_PROGRESS/COMPLETED/UNABLE_TO_RESPOND/CANCELLED states; EXPIRED is tested only when a timeout policy is approved.
- One agency acknowledgement/completion/inability never mutates the other assignment or incident state.
- Non-acknowledgement produces an overdue/manual-follow-up state by default; no emergency dispatch or external escalation occurs.
- Assignment cancellation/reassignment preserves prior AssignmentStatusHistory and creates a new assignment.
- Partial completion and resolution with outstanding nonterminal assignments follow the approved aggregation/override rule.
- Unauthorized resolve/close/reopen and invalid/stale transitions are denied and audited.
- Notification CREATED/PENDING/DELIVERED_SIMULATED/FAILED/READ/CANCELLED does not mutate assignment or incident lifecycle.

### Evidence and Location

- Upload authorization is short-lived, object-scoped, operation-scoped, and unusable for arbitrary paths or unauthorized transfers.
- Backend-mediated upload fallback is tested if the selected provider lacks scoped direct upload.
- Upload failure, object-store outage, invalid type/size, integrity failure, quarantine/scanning failure, expiry, and deletion never expose unavailable evidence.
- Only AVAILABLE EvidenceAssets can be retrieved; role/assignment/object authorization is enforced for Police, Hospital, Admin, and AI_SERVICE.
- Evidence retrieval is audited; denial does not reveal object existence or storage paths.
- Camera coordinates, approved GPS, uncertain inference, and manual correction retain distinct LocationProvenance; no precision is fabricated.
- Unauthorized location read/correction is denied and audited.

### Source, Security, and Audit

- VideoSource owner authorization, source revocation, unavailable input, timestamp provenance, and controlled-file demo path are tested.
- Source/camera credentials, JWTs, tokens, raw footage, and unnecessary personal data never appear in logs, audit records, fixtures, or repository files.
- Audit completeness covers authentication success/failure, roles, source authorization, review, incident creation, assignments/response, resolution/closure/reopen, evidence transfer/retrieval/deletion, location correction, and override.
- Audit persistence failure follows an agreed fail-safe/recovery policy and is not reported as a completed audited action.
- Error handling avoids stack traces and object-existence disclosure.

## Test Data and Approval Boundaries

Use synthetic or explicitly approved source videos and labeled evaluation data. Do not use real incident footage or personal data without documented authorization. Timeout intervals, retention, evidence scanning policy, incident override authority, and performance thresholds must be approved before tests assert them. These are planned scenarios, not claims of implementation or execution.

Keep fixtures synthetic or otherwise approved and privacy-safe. Do not use real incident footage or personal data without documented authorization. Record what was run and its result; do not fabricate test outcomes. Agree on CI checks and coverage targets before setting thresholds.
