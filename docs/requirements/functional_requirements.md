# Functional Requirements

**Status:** REVISED_DRAFT — pending team approval. Some supporting behavior is implemented; the project owner approved the Police-first verification and simulated Hospital response workflow on 2026-11-19, but this does not enable runtime permissions.
**Priority:** Must = required for the controlled prototype; Should = valuable if feasible; Could = optional.
**Actor and authority:** The project owner approved the specifically authorized human Police reviewer role class and Police-before-Hospital order. Individual reviewer scope, Hospital routing, and other assignment authority remain open and are identified below.

## FR-001 — Authenticate users

- **Description:** The backend shall authenticate registered users before granting protected client access.
- **Actor:** ADMIN, POLICE, HOSPITAL.
- **Preconditions:** The account exists and is enabled.
- **Main flow:** User submits credentials; backend validates them; backend returns an authenticated session or token; client uses it for protected requests.
- **Alternative flow:** Invalid credentials or disabled account produce a safe denial without confirming account-sensitive details.
- **Postconditions:** Successful authentication is attributable to a user; failed attempts do not grant access.
- **Priority:** Must.
- **Acceptance criteria:** Protected requests without valid credentials are denied; valid enabled accounts can authenticate; errors contain no secrets or stack traces.

## FR-002 — Manage users and roles

- **Description:** An authorized administrator shall create, update, disable, and assign the supported prototype roles to user accounts.
- **Actor:** ADMIN.
- **Preconditions:** Administrator is authenticated and authorized.
- **Main flow:** Administrator selects an account action; backend validates input and role; backend records the change and audit event.
- **Alternative flow:** Duplicate identity, invalid role, or insufficient permission is rejected with a safe error.
- **Postconditions:** User and role state is updated only after backend authorization.
- **Priority:** Must.
- **Acceptance criteria:** Non-admin users cannot administer accounts; only ADMIN, POLICE, and HOSPITAL are accepted roles unless the role model is formally revised; changes are auditable.

## FR-003 — Process only authorized video inputs

- **Description:** The AI processing boundary shall process only a registered/authorized VideoSource or explicitly approved controlled file.
- **Actor:** Source owner/operator supplies input; proposed ADMIN/authorized operator manages registry; AI service validates.
- **Preconditions:** Source ownership and processing permission are documented; input limits and policy reference are available.
- **Main flow:** Backend registry returns authorized source metadata; AI validates source reference, format, and policy; input and source/time provenance travel with processing.
- **Alternative flow:** Unauthorized, revoked, corrupt, unsupported, unavailable, or over-limit input is rejected/failed separately from a no-candidate outcome.
- **Postconditions:** Processing outcome is attributable to VideoSource and source timestamp; media follows approved retention.
- **Priority:** Must.
- **Acceptance criteria:** Unauthorized or invalid sources cannot produce accepted DetectionEvents; source identity and timestamp are preserved; failure is distinguishable from a completed analysis with no candidate.

## FR-004 — Generate DetectionEvents

- **Description:** The AI service shall produce distinct machine-generated DetectionEvents from relevant observations and temporal analysis, preserving timing, source, and uncertainty.
- **Actor:** AI service.
- **Preconditions:** Input passed FR-003 validation and an approved model/configuration is available.
- **Main flow:** Service detects and, where useful, tracks objects; evaluates temporal evidence; emits one or more uniquely identified DetectionEvents with provenance and supporting evidence metadata.
- **Alternative flow:** Insufficient evidence yields no event or an explicitly uncertain observation; model/input failure is reported separately.
- **Postconditions:** Each event remains distinct from an AccidentCandidate and AccidentIncident.
- **Priority:** Must.
- **Acceptance criteria:** Each event has a stable submission identity, source/time provenance, processing outcome, and uncertainty metadata where available; AI output never claims human verification.

## FR-005 — Review AccidentCandidates

- **Description:** Backend shall maintain candidate lifecycle RECEIVED, UNDER_REVIEW, VERIFIED, REJECTED; only an authorized human may decide VERIFIED or REJECTED.
- **Actor:** AI service supplies observations; a specifically authorized human Police reviewer decides under the owner-approved workflow. Reviewer identity/group, scope, and decision criteria remain TBD. This is not authority for every `POLICE` user; `ADMIN` is not substituted by default.
- **Preconditions:** One or more validated DetectionEvents are associated with a candidate; candidate is RECEIVED.
- **Main flow:** Backend sets UNDER_REVIEW; authorized reviewer examines temporal evidence, uncertainty, source and evidence provenance; reviewer submits decision/rationale; backend authorizes and records it.
- **Alternative flow:** Insufficient/contradictory evidence remains UNDER_REVIEW; unavailable review capacity does not confirm it; rejected candidate is retained per policy.
- **Postconditions:** Candidate decision, actor, reason, time, related DetectionEvents, and evidence references are auditable; no incident exists for rejected candidates.
- **Priority:** Must.
- **Acceptance criteria:** AI_SERVICE cannot change candidate to VERIFIED/REJECTED; invalid transitions are denied; only a specifically authorized Police reviewer in approved scope can decide; reviewer identity, scope, permitted information, and criteria remain open for approval.

## FR-006 — Manage EvidenceAssets and media lifecycle

- **Description:** Backend shall own EvidenceAsset metadata/access/lifecycle; object storage holds bytes only. Candidate and resulting incident may reference the same asset.
- **Actor:** AI_SERVICE generates/uploads scoped asset; backend authorizes/validates; scoped users retrieve.
- **Preconditions:** Evidence purpose, media policy, and authorized candidate association exist.
- **Main flow:** Asset moves through PENDING_UPLOAD, UPLOADING, QUARANTINED, AVAILABLE; validation/integrity checks succeed before availability.
- **Alternative flow:** Upload, validation, scanning, storage, or integrity failure leaves asset FAILED/QUARANTINED and unavailable; retry/manual recovery is recorded.
- **Postconditions:** Backend stores metadata and provenance; media remains private and subject to retention/deletion.
- **Priority:** Must.
- **Acceptance criteria:** No public evidence bucket or broad permanent credential is used; only validated AVAILABLE assets can be retrieved; unauthorized object access is denied and audited; terminal EXPIRED/DELETED states prevent retrieval.

## FR-007 — Receive and deduplicate DetectionEvents

- **Description:** Backend shall authenticate AI_SERVICE, validate each DetectionEvent, and safely handle event retries independently from candidate similarity.
- **Actor:** AI_SERVICE submits; backend intake validates.
- **Preconditions:** AI_SERVICE machine identity is authenticated; event identity and source provenance are present under a future approved contract.
- **Main flow:** Backend validates caller/source/payload; stores one distinct event and intake outcome; repeated identical event identity returns/links to the prior outcome; new event is associated to or creates a candidate.
- **Alternative flow:** Invalid identity/source/payload is rejected; uncertain candidate match is flagged for human review without silently merging.
- **Postconditions:** Event-level idempotency preserves event provenance; candidate association does not erase distinct events.
- **Priority:** Must.
- **Acceptance criteria:** Invalid AI_SERVICE cannot mutate state; identical event retry creates no duplicate event/candidate/assignment; distinct observations remain individually traceable; mobile and AI clients cannot write directly to PostgreSQL.

## FR-008 — Create independent ResponseAssignments

- **Description:** Backend shall represent each assignment from one verified AccidentIncident to one eligible Police or Hospital target as a separate ResponseAssignment.
- **Actor:** ADMIN (proposed; assignment policy TBD).
- **Preconditions:** An OPEN/eligible AccidentIncident exists; target is eligible under the approved assignment policy.
- **Main flow:** Authorized assignment actor selects a target; backend checks scope; creates that target's PENDING assignment and history; a second agency receives its own assignment.
- **Alternative flow:** Ineligible target, stale incident, or duplicate active target assignment is rejected or linked safely; one agency action never changes another assignment.
- **Postconditions:** Each target and its status/history are independently scoped and auditable.
- **Priority:** Must.
- **Acceptance criteria:** Only a verified candidate's linked incident can be assigned; one incident can have independent Police and Hospital assignments; role scope is checked; reassignment preserves/cancels old assignment and creates a new record.

## FR-009 — Track notification state separately

- **Description:** Backend shall keep Notification delivery/read state separate from candidate, incident, and assignment state.
- **Actor:** Backend notification component; ADMIN, POLICE, HOSPITAL as recipients.
- **Preconditions:** A permitted workflow event occurs and recipient scope is known.
- **Main flow:** Notification progresses through CREATED, PENDING, DELIVERED_SIMULATED, READ, FAILED, or CANCELLED as applicable; delivery/read does not mutate assignment acknowledgement.
- **Alternative flow:** Simulated failure/retry is recorded; no live external dispatch is attempted.
- **Postconditions:** Notification outcome is traceable and explicitly marked simulated.
- **Priority:** Must.
- **Acceptance criteria:** Prototype sends no real Police/Hospital emergency notification; notification creation, delivery, or read cannot set an assignment ACKNOWLEDGED or incident RESPONSE_ACTIVE.

## FR-010 — Preserve LocationProvenance

- **Description:** Backend shall retain origin, source, timestamp, uncertainty/accuracy, verification status, and authorized correction history for each location claim.
- **Actor:** AI/source supplies provenance; authorized human may correct; backend enforces access.
- **Preconditions:** Location has a documented source such as camera registry, approved GPS, or human verification.
- **Main flow:** Backend stores a location claim with its source/time/uncertainty and propagates provenance when candidate becomes incident.
- **Alternative flow:** Missing/uncertain location remains explicitly unknown/imprecise; camera position is not equated to accident position.
- **Postconditions:** Authorized display exposes provenance and uncertainty without overstating precision.
- **Priority:** Should.
- **Acceptance criteria:** Camera and accident location are distinguishable; every displayed claim has origin/time/uncertainty where available; no precision is fabricated; authorized corrections are attributable; map failure does not block review.

## FR-011 — Manage Police ResponseAssignments

- **Description:** Police users shall view only their authorized assignments and independently update their own simulated response activity.
- **Actor:** POLICE.
- **Preconditions:** User is authenticated and assignment is in approved scope.
- **Main flow:** User reviews permitted incident/evidence; acknowledges PENDING assignment; records progress/complete/unable-to-respond status and rationale as allowed.
- **Alternative flow:** Out-of-scope, stale, or invalid transition is denied; other agency assignment is unchanged.
- **Postconditions:** Assignment and Response history record actor/time; no real operational action is implied.
- **Priority:** Must.
- **Acceptance criteria:** Police user can affect only assigned Police target state; acknowledgement does not acknowledge incident or Hospital assignment; response is labelled simulated; updates are audited.

## FR-012 — Manage Hospital ResponseAssignments

- **Description:** Hospital users shall view the minimum information needed for their authorized assignment and independently update simulated readiness.
- **Actor:** HOSPITAL.
- **Preconditions:** User is authenticated and a Hospital assignment is in approved scope.
- **Main flow:** User reviews minimized incident summary; acknowledges own PENDING assignment; records readiness/response activity and completion or inability as permitted.
- **Alternative flow:** Out-of-scope, stale, or invalid transition is denied; Police assignment remains unchanged.
- **Postconditions:** Assignment and Response history record actor/time; readiness is not represented as treatment.
- **Priority:** Must.
- **Acceptance criteria:** Hospital user can affect only own scoped assignment; readiness does not claim treatment; data are minimized and updates are audited.

## FR-013 — Provide Admin oversight

- **Description:** Admin users shall view system-level operational summaries and perform authorized user, incident review, and assignment actions.
- **Actor:** ADMIN.
- **Preconditions:** User is authenticated and has the relevant permission.
- **Main flow:** Admin reviews authorized summaries; takes a permitted action; backend validates, records, and audits the action.
- **Alternative flow:** Restricted evidence or unsupported action is denied; system failures are surfaced without leaking sensitive data.
- **Postconditions:** Administrative actions and resulting state are traceable.
- **Priority:** Must.
- **Acceptance criteria:** Admin actions are checked server-side and audited; oversight does not imply emergency dispatch capability.

## FR-014 — View incident and assignment history

- **Description:** Authorized users shall retrieve separately scoped IncidentStatusHistory and AssignmentStatusHistory, plus Response activity for authorized targets.
- **Actor:** ADMIN, POLICE, HOSPITAL according to scope.
- **Preconditions:** User is authenticated and authorized for the incident.
- **Main flow:** Client requests incident or assignment history; backend checks object/assignment scope and returns ordered events with actor attribution where permitted.
- **Alternative flow:** Out-of-scope access is denied; missing history is represented without inventing events.
- **Postconditions:** History remains read-only to ordinary users.
- **Priority:** Should.
- **Acceptance criteria:** Incident history is not a copy of assignment history; Police/Hospital see only authorized target activity; entries are ordered, attributable, and not alterable through ordinary client operations.

## FR-015 — Produce reports and analytics

- **Description:** Admin users may view aggregate prototype metrics derived from authorized records, subject to privacy and data-quality limits.
- **Actor:** ADMIN.
- **Preconditions:** Data exists and aggregation is permitted.
- **Main flow:** Backend calculates a documented aggregate; interface labels the period, population, and limitations.
- **Alternative flow:** Insufficient or unreliable data is reported as unavailable rather than presented as a performance claim.
- **Postconditions:** Aggregate results do not expose unnecessary personal or sensitive media data.
- **Priority:** Could.
- **Acceptance criteria:** Reports distinguish prototype observations from validated model performance and do not claim unmeasured accuracy or response impact.

## FR-016 — Audit security-relevant actions

- **Description:** The backend shall record attributable security and lifecycle actions needed for accountability.
- **Actor:** Backend service.
- **Preconditions:** A security-relevant action or lifecycle transition occurs.
- **Main flow:** Backend records actor/service, action, target reference, time, and outcome while minimizing sensitive payload.
- **Alternative flow:** Audit persistence failure is handled according to an approved fail-safe policy; the action is not silently reported as audited.
- **Postconditions:** Authorized reviewers can inspect scoped audit history.
- **Priority:** Must.
- **Acceptance criteria:** Role changes, access-sensitive actions, verification, assignment, and lifecycle transitions produce attributable records; logs contain no credentials or unnecessary raw video.

## FR-017 — Associate multiple DetectionEvents with one AccidentCandidate

- **Description:** Backend shall preserve each distinct DetectionEvent while allowing multiple related events to contribute to one AccidentCandidate.
- **Actor:** Backend service; authorized reviewer resolves uncertain associations.
- **Preconditions:** Events have passed authentication, source authorization, and payload validation.
- **Main flow:** Backend applies an approved association method using provenance; confidently related events link to a candidate; each event retains its original identity and observations.
- **Alternative flow:** If candidate match is uncertain, backend flags it for review rather than silently merging or discarding.
- **Postconditions:** Event-to-candidate provenance is preserved and reviewable.
- **Priority:** Must.
- **Acceptance criteria:** Multiple events can link to one candidate; each remains individually traceable; candidate-level deduplication does not replace event idempotency; uncertain matches are auditable.

## FR-018 — Enforce distinct candidate and incident concepts

- **Description:** Backend shall maintain AccidentCandidate separately from AccidentIncident.
- **Actor:** Backend service.
- **Preconditions:** A candidate has been accepted and is available for human review.
- **Main flow:** Candidate moves through RECEIVED, UNDER_REVIEW, VERIFIED, or REJECTED; verification decision remains on candidate and its history.
- **Alternative flow:** Rejection or pending review creates no AccidentIncident; transaction failure during verification leaves candidate/incident relationship consistent.
- **Postconditions:** Candidate, its events/evidence, and any resulting incident remain linked without conflating lifecycles.
- **Priority:** Must.
- **Acceptance criteria:** No DetectionEvent or unverified candidate is presented as an authoritative incident; rejected candidates remain distinguishable; only backend may create incident.

## FR-019 — Create an AccidentIncident after verification

- **Description:** Backend shall create exactly one authoritative AccidentIncident only after a specifically authorized human Police reviewer has verified the linked candidate under the owner-approved workflow.
- **Actor:** Backend service applies an authorized Police reviewer decision.
- **Preconditions:** Candidate is UNDER_REVIEW; reviewer identity, scope, evidence, and decision are valid.
- **Main flow:** Backend transaction records candidate VERIFIED, creates linked incident in OPEN state, appends Candidate/Incident status history and audit event.
- **Alternative flow:** Rejected candidate creates no incident; transaction failure creates neither a falsely verified candidate nor orphan incident and can be safely retried.
- **Postconditions:** One incident has provenance to its candidate, source DetectionEvents, location claims, and evidence.
- **Priority:** Must.
- **Acceptance criteria:** Incident creation is backend-only and atomic with verification; retries do not create duplicate incidents; actor, reason, and time are retained.

## FR-032 — Create a Hospital response request after Police verification

- **Description:** After a Police-verified candidate has atomically produced one linked `OPEN` AccidentIncident, the backend shall create a response request for the designated Hospital. An authorized Hospital user shall record request acknowledgement and availability or inability to respond, followed by a distinct simulated ambulance-dispatch decision and subsequent simulated response status.
- **Actor:** Backend creates the incident-linked request; a specifically authorized user in the designated Hospital scope records acknowledgement, availability/inability, and simulated response events.
- **Preconditions:** Police verification is valid and the linked incident is committed; the target Hospital is designated under an approved routing/eligibility policy.
- **Main flow:** Backend creates a request traceable to the incident. The Hospital user records acknowledgement and availability or inability. If the Hospital records a dispatch decision, that decision and later response status are stored separately and labeled simulated.
- **Alternative flow:** Rejected or inconclusive candidates produce no incident or Hospital request. Request failure does not create a duplicate incident or falsely indicate Hospital receipt; retry and failure recovery must be idempotent and auditable. A missing/ineligible target does not trigger arbitrary routing.
- **Postconditions:** Incident, request, Hospital acknowledgement/availability, simulated dispatch decision, and subsequent response status remain distinct and independently scoped. No real emergency service is contacted.
- **Priority:** Must for the controlled prototype workflow; exact implementation contract remains pending.
- **Acceptance criteria:** The project-owner-approved Police-before-Hospital order is enforced; request creation occurs only after incident commit and links to that incident and the designated Hospital; retries do not duplicate requests; only the scoped Hospital user can update its request; acknowledgement is not dispatch confirmation; all dispatch/response labels are simulated; no real Police, Hospital, ambulance, push, or emergency endpoint is called.
- **Governance note:** Workflow sequence approved by the project owner on 2026-11-19. Reviewer/target identities, routing, exact response states/transitions, field access, and API contracts remain pending under OAD-012/013/018.

## FR-020 — Create independent assignments for eligible agencies

- **Description:** Backend shall support multiple ResponseAssignments for one incident, each addressed to one eligible Police or Hospital response target.
- **Actor:** ADMIN or approved assignment mechanism (authority TBD); backend enforces eligibility.
- **Preconditions:** OPEN/eligible AccidentIncident exists and assignment target is authorized.
- **Main flow:** Actor creates separate assignment for each target; each starts PENDING with independent target, status, and history; assignment may generate its own simulated Notification.
- **Alternative flow:** Duplicate active assignment to same target is flagged/rejected; one agency assignment failure does not cancel or alter another.
- **Postconditions:** Incident-to-assignment relationships and target scope are auditable.
- **Priority:** Must.
- **Acceptance criteria:** One incident may have independent Police and Hospital assignments; each assignment references exactly one incident and one eligible target; no shared ACK state exists.

## FR-021 — Manage ResponseAssignment lifecycle

- **Description:** Backend shall validate each assignment's independent PENDING, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, UNABLE_TO_RESPOND, CANCELLED, or policy-approved EXPIRED state.
- **Actor:** Assigned POLICE/HOSPITAL user; authorized ADMIN/assignment actor; backend for approved expiration only.
- **Preconditions:** Assignment exists and caller has its object-level permission.
- **Main flow:** Assigned user acknowledges and records activity/completion; authorized actor may cancel/reassign; each state change appends AssignmentStatusHistory and Response where applicable.
- **Alternative flow:** Invalid/stale transition is denied; reassignment cancels/supersedes old assignment and creates a new assignment without deleting history.
- **Postconditions:** Each target's lifecycle remains independent.
- **Priority:** Must.
- **Acceptance criteria:** Only assigned user can acknowledge/update their target's assignment; UNABLE_TO_RESPOND requires reason; EXPIRED cannot be used absent approved timeout policy; invalid transition is audited.

## FR-022 — Manage incident lifecycle independently

- **Description:** Backend shall manage AccidentIncident states OPEN, RESPONSE_ACTIVE, RESOLVED, CLOSED independently of assignment and notification states.
- **Actor:** Backend derives RESPONSE_ACTIVE from response activity; authorized human decides resolution/closure (authority TBD).
- **Preconditions:** AccidentIncident exists in OPEN or a valid later state.
- **Main flow:** OPEN transitions to RESPONSE_ACTIVE when response activity starts; authorized reviewer records RESOLVED with rationale after assignment outcomes are addressed; separately authorized actor closes a resolved incident.
- **Alternative flow:** Acknowledgement alone does not mark RESPONSE_ACTIVE; unresolved nonterminal assignments prevent resolution under the proposed rule unless an approved, audited override applies.
- **Postconditions:** IncidentStatusHistory records actor/source, state, time, and reason; assignment states remain unchanged.
- **Priority:** Must.
- **Acceptance criteria:** Incident cannot enter CLOSED directly from OPEN/RESPONSE_ACTIVE; assignment ACK does not mutate incident; resolution and closure are distinct; no unauthorized transition succeeds.

## FR-023 — Aggregate multi-agency outcomes without state conflation

- **Description:** Backend shall preserve Police and Hospital assignment status independently and apply an explicit incident-level resolution rule.
- **Actor:** Backend; authorized resolver.
- **Preconditions:** One or more ResponseAssignments exist.
- **Main flow:** Backend presents each target's latest independent state; incident resolver reviews all assignments and records an incident-level decision.
- **Alternative flow:** One assignment remains PENDING/ACKNOWLEDGED/IN_PROGRESS; incident stays unresolved unless an approved override with rationale is recorded.
- **Postconditions:** Partial completion and unresolved targets remain visible and attributable.
- **Priority:** Must.
- **Acceptance criteria:** One agency acknowledgement, inability, completion, or failure never overwrites another assignment; incident resolution does not imply treatment or real-world dispatch.

## FR-024 — Maintain Notification delivery lifecycle separately

- **Description:** Backend shall maintain notification states CREATED, PENDING, DELIVERED_SIMULATED, FAILED, READ, and CANCELLED separately from incident and assignment state.
- **Actor:** Backend notification component and authorized recipient.
- **Preconditions:** A permitted prototype notification event exists.
- **Main flow:** Backend records simulated notification lifecycle; recipient may mark it READ within scope; delivery state remains non-authoritative.
- **Alternative flow:** Failure/retry/cancellation changes only Notification state; it never acknowledges/cancels an assignment.
- **Postconditions:** Notification and assignment histories remain separate.
- **Priority:** Must.
- **Acceptance criteria:** No notification state automatically changes assignment or incident; all delivery is labeled simulated; no real emergency service is contacted.

## FR-025 — Authorize evidence upload

- **Description:** Backend shall authorize evidence upload for a specific EvidenceAsset, candidate, and AI_SERVICE identity.
- **Actor:** AI_SERVICE requests authorization; backend checks scope; object-storage provider executes transfer if supported.
- **Preconditions:** Candidate and metadata are valid; AI_SERVICE owns the submission capability.
- **Main flow:** Backend creates server-controlled object reference and PENDING_UPLOAD metadata; returns a short-lived, single-object, operation-scoped upload authorization where supported.
- **Alternative flow:** If scoped direct upload is unsupported, use backend-mediated upload; unauthorized, expired, or reused authorization is denied.
- **Postconditions:** Upload permission cannot access arbitrary objects or unrelated evidence.
- **Priority:** Must.
- **Acceptance criteria:** No broad permanent storage credential is given to AI_SERVICE; object key is server-controlled/unpredictable; upload authorization is scoped and expires; fallback is documented.

## FR-026 — Validate evidence before making it available

- **Description:** Backend shall track EvidenceAsset states and validate uploaded media before allowing retrieval.
- **Actor:** Backend and storage-validation integration.
- **Preconditions:** EvidenceAsset is PENDING_UPLOAD or UPLOADING.
- **Main flow:** On upload completion, backend verifies expected object identity, metadata, allowed type/size, and integrity/checksum where supported; asset enters QUARANTINED while required scanning/validation runs and AVAILABLE only after success.
- **Alternative flow:** Upload, integrity, scan, size, type, or storage failure leaves asset FAILED/QUARANTINED; retry or manual recovery is audited.
- **Postconditions:** Candidate/incident status is not changed by media failure.
- **Priority:** Must.
- **Acceptance criteria:** Only AVAILABLE evidence can be retrieved; rejected/unauthorized/unvalidated media is not publicly accessible; EXPIRED/DELETED evidence is unavailable.

## FR-027 — Retrieve evidence with object-level authorization

- **Description:** Backend shall authorize each EvidenceAsset read using human identity, role, candidate/incident relationship, assignment scope, and evidence state.
- **Actor:** ADMIN, POLICE, HOSPITAL according to approved scope.
- **Preconditions:** User is authenticated; asset is AVAILABLE; resource relationship and policy are known.
- **Main flow:** Client requests by logical asset reference; backend checks permission and returns media through a controlled backend stream or short-lived restricted retrieval authorization.
- **Alternative flow:** Denied/unavailable requests return safe outcome without revealing object existence or storage path.
- **Postconditions:** Sensitive retrieval attempt and successful access are auditable.
- **Priority:** Must.
- **Acceptance criteria:** No mobile client receives broad storage credentials or arbitrary object-path access; role alone does not expose all evidence; authorized access obeys least privilege.

## FR-028 — Register and authorize VideoSources

- **Description:** Backend shall conceptually manage VideoSource identity, owner, source type, authorization status, location reference, availability/health information, input configuration reference, timestamp provenance, processing policy, and retention/privacy policy.
- **Actor:** Authorized source owner/operator supplies information; proposed ADMIN/authorized operator records approval; AI service validates authorization.
- **Preconditions:** Ownership and processing purpose are documented.
- **Main flow:** Source is registered, reviewed, authorized, and then referenced by input/DetectionEvents; authorization can be suspended or revoked.
- **Alternative flow:** Missing permission, revoked source, unavailable camera, or credential error blocks processing and is distinct from no candidate.
- **Postconditions:** Every accepted event traces to an authorized VideoSource and applicable policy.
- **Priority:** Must.
- **Acceptance criteria:** Approved controlled-file input remains available for demonstrations; source health/unavailability is distinguishable from no-candidate; credentials are never committed; ingestion mechanism remains replaceable; unauthorized source cannot produce accepted events.

## FR-029 — Preserve location origin and correction history

- **Description:** Backend shall associate LocationProvenance with camera, GPS, inferred, or manually verified location claims.
- **Actor:** AI/source submits provenance; authorized human corrects; backend secures data.
- **Preconditions:** A location claim has a documented source and timestamp when available.
- **Main flow:** Backend preserves claim origin, associated VideoSource, source time, accuracy/uncertainty, verification status, and correction history through event/candidate/incident association.
- **Alternative flow:** Unknown precision remains unknown; camera coordinates are shown as camera position, not accident position.
- **Postconditions:** Location claims can be interpreted without overstating precision.
- **Priority:** Must.
- **Acceptance criteria:** No fabricated GPS precision; camera vs inferred/manual incident position is distinguishable; manual corrections identify actor/time/reason; access is scoped and audited.

## FR-030 — Record mandatory audit events

- **Description:** Backend shall create attributable, timestamped audit records for security, candidate, incident, assignment, evidence, and administrative actions.
- **Actor:** Backend services using human or machine actor identity.
- **Preconditions:** A listed security-sensitive action or transition occurs.
- **Main flow:** Audit records actor/service, action, target, time, outcome, and safe correlation data before reporting success.
- **Alternative flow:** Audit persistence failure follows a reviewed fail-safe policy; it is not silently reported as logged.
- **Postconditions:** Ordinary users cannot silently overwrite audit history; access and retention are controlled.
- **Priority:** Must.
- **Acceptance criteria:** Authentication success/failure, role creation/modification, user activation/deactivation, source authorization, candidate review, incident creation, assignments, acknowledgement, response, resolution/closure/reopen, evidence upload/retrieval/deletion/retention, location correction, and override are auditable; no secrets/raw media are logged.

## FR-031 — Handle non-acknowledgement, timeout, and reassignment safely

- **Description:** Backend shall represent overdue assignments and approved timeout outcomes without external escalation.
- **Actor:** Backend displays overdue state; authorized Admin/assignment actor follows up; system may expire only under approved policy.
- **Preconditions:** Assignment remains PENDING beyond a proposed threshold or reassignment is requested.
- **Main flow:** Default prototype behavior marks an overdue indicator for manual review; authorized actor may cancel old assignment and create a new one, preserving history.
- **Alternative flow:** If approved timeout policy exists, system may transition to EXPIRED and audit rule/version; absent policy, no automatic expiration occurs.
- **Postconditions:** No non-acknowledgement or timeout triggers real alert, dispatch, or another agency's state change.
- **Priority:** Must.
- **Acceptance criteria:** Timeout interval is not fabricated; manual follow-up is proposed default; reassignment is auditable and independent; emergency escalation is impossible in prototype.

## Related Workflows

See [system workflow](../workflows/system_workflow.md), [AI detection workflow](../workflows/ai_detection_workflow.md), [incident response workflow](../workflows/incident_response_workflow.md), [user-role workflows](../workflows/user_role_workflows.md), and [requirements traceability](requirements_traceability.md).
