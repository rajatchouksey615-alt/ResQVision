# Functional Requirements

**Status:** Draft for team review; none of these behaviors is implemented.
**Priority:** Must = required for the controlled prototype; Should = valuable if feasible; Could = optional.
**Actor and authority:** Where a reviewer or assignment authority is not yet approved, the requirement records a proposed actor and leaves approval open.

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

## FR-003 — Manage approved video inputs

- **Description:** The AI processing boundary shall accept only inputs permitted by the approved source and data-use policy.
- **Actor:** AI service; source owner/operator supplies input.
- **Preconditions:** Input source and processing purpose are authorized.
- **Main flow:** Service validates source, format, and policy metadata; accepted input enters processing with a traceable source reference.
- **Alternative flow:** Unsupported, unauthorized, corrupt, or unavailable input is rejected or marked failed without creating a verified incident.
- **Postconditions:** Processing outcome and source reference are traceable; raw media retention follows an approved policy.
- **Priority:** Must.
- **Acceptance criteria:** Unauthorized or invalid inputs do not enter normal processing; failure outcomes can be distinguished from a no-accident result.

## FR-004 — Generate detection candidates

- **Description:** The AI service shall produce candidate events from relevant detections and temporal observations, preserving timing and uncertainty.
- **Actor:** AI service.
- **Preconditions:** Input passed FR-003 validation and an approved model/configuration is available.
- **Main flow:** Service detects and, where useful, tracks objects; evaluates temporal evidence; emits a candidate with a unique event reference and supporting metadata.
- **Alternative flow:** Insufficient evidence yields no candidate or an explicitly uncertain outcome; model/input failure is reported separately.
- **Postconditions:** Candidate output is distinguishable from an incident or confirmed accident.
- **Priority:** Must.
- **Acceptance criteria:** Every emitted candidate has a source reference, event time/context, verification status, and provenance; the output does not claim certainty unsupported by the pipeline.

## FR-005 — Verify accident candidates

- **Description:** A candidate shall pass a documented temporal verification process and any required authorized human review before entering VERIFIED.
- **Actor:** AI service provides evidence; proposed authorized human reviewer makes the authoritative decision. Reviewer role is TBD.
- **Preconditions:** Candidate is recorded as DETECTED and is available for verification.
- **Main flow:** Candidate enters UNDER_VERIFICATION; system presents temporal evidence and uncertainty; approved reviewer or policy evaluates it; backend records VERIFIED only when required criteria are met.
- **Alternative flow:** Evidence is insufficient or contradictory and remains pending or is rejected; unavailable review capacity does not silently confirm the event.
- **Postconditions:** Decision, rationale/reference, actor, and time are auditable.
- **Priority:** Must.
- **Acceptance criteria:** AI score alone cannot set an incident to VERIFIED; a rejected candidate cannot be assigned for response; verification thresholds and reviewer authority remain explicit TBDs until approved.

## FR-006 — Capture and manage evidence references

- **Description:** The system shall associate approved evidence references and metadata with a candidate or incident while controlling access to the underlying media.
- **Actor:** AI service creates evidence; backend manages references; authorized users view permitted evidence.
- **Preconditions:** Evidence generation and storage are permitted by policy.
- **Main flow:** AI service submits evidence metadata; backend validates the reference and records ownership/provenance; an authorized user requests access through a controlled path.
- **Alternative flow:** Missing, unavailable, expired, or unauthorized evidence is reported without exposing a public storage location.
- **Postconditions:** Metadata and access decisions are auditable; media remains subject to retention and deletion policy.
- **Priority:** Must.
- **Acceptance criteria:** Private media is not stored in the repository or exposed through an unrestricted link; unauthorized users cannot retrieve evidence.

## FR-007 — Create and maintain incident records

- **Description:** The backend shall own the authoritative incident record and its lifecycle.
- **Actor:** Backend service; AI service submits candidates; authorized users review.
- **Preconditions:** A candidate was received through an authenticated service boundary.
- **Main flow:** Backend validates and deduplicates the event where possible; records a DETECTED candidate and its provenance; updates lifecycle only through an authorized transition.
- **Alternative flow:** Invalid or duplicate submissions are safely rejected or linked to an existing record without unintended duplicate response work.
- **Postconditions:** One authoritative backend record represents a managed incident; changes are auditable.
- **Priority:** Must.
- **Acceptance criteria:** Mobile and AI clients cannot write directly to PostgreSQL; invalid transitions are rejected; duplicate handling is idempotent where an agreed event identity supports it.

## FR-008 — Assign verified incidents

- **Description:** An authorized administrator shall assign a verified incident to an eligible Police or Hospital response group for simulated coordination.
- **Actor:** ADMIN (proposed; assignment policy TBD).
- **Preconditions:** Incident is VERIFIED; target is active and eligible under an approved assignment policy.
- **Main flow:** Administrator selects target; backend checks authorization and scope; backend records ASSIGNED and an audit event.
- **Alternative flow:** Ineligible target or stale incident state is rejected; assignment can be retried after review.
- **Postconditions:** Assignment and responsible group are visible only to authorized users.
- **Priority:** Must.
- **Acceptance criteria:** Unverified and rejected candidates cannot be assigned; unauthorized users cannot assign; assignment changes are auditable.

## FR-009 — Record simulated notifications

- **Description:** The backend shall support prototype notification records or simulated delivery results without contacting real emergency organizations.
- **Actor:** Backend notification component; ADMIN, POLICE, HOSPITAL as recipients.
- **Preconditions:** A permitted workflow event occurs and recipient scope is known.
- **Main flow:** Backend creates a simulated notification record; status is available for review; retries do not create unintended duplicate notifications.
- **Alternative flow:** Simulated delivery failure is recorded for inspection; no live external dispatch is attempted.
- **Postconditions:** Notification outcome is traceable and explicitly marked simulated.
- **Priority:** Must.
- **Acceptance criteria:** Prototype execution cannot send real emergency alerts; notification records identify simulated status and do not claim dispatch.

## FR-010 — Manage location information

- **Description:** The system shall associate only the location detail needed for authorized incident review, subject to source precision and privacy policy.
- **Actor:** AI service supplies source-derived location when available; backend controls access; authorized users view it.
- **Preconditions:** Location was lawfully obtained and its precision is known.
- **Main flow:** Backend records a location reference and provenance; authorized client displays it using an approved map provider if one is selected.
- **Alternative flow:** Unknown or imprecise location is labeled as such; map/provider failure does not prevent incident review.
- **Postconditions:** Location access is scoped and auditable.
- **Priority:** Should.
- **Acceptance criteria:** No location is fabricated; unavailable or uncertain location is represented honestly; map provider remains TBD.

## FR-011 — Review incidents as Police

- **Description:** Police users shall view incidents within their approved assignment or jurisdictional scope and update permitted simulated response states.
- **Actor:** POLICE.
- **Preconditions:** User is authenticated and incident is in scope.
- **Main flow:** User reviews incident and permitted evidence; acknowledges assignment; records response progress or resolution with an auditable update.
- **Alternative flow:** Out-of-scope or stale-state actions are denied; unavailable evidence is clearly indicated.
- **Postconditions:** Response state and actor/time are recorded.
- **Priority:** Must.
- **Acceptance criteria:** Police users cannot access incidents outside scope or change administrative roles; every response update is authorized and auditable.

## FR-012 — Review incidents as Hospital

- **Description:** Hospital users shall view the minimum information needed for an approved assignment and update simulated readiness status.
- **Actor:** HOSPITAL.
- **Preconditions:** User is authenticated and incident is in scope.
- **Main flow:** User reviews permitted incident summary; acknowledges the assignment; records readiness or status updates.
- **Alternative flow:** Out-of-scope or stale-state actions are denied; sensitive details not required for the workflow remain hidden.
- **Postconditions:** Readiness update and actor/time are recorded.
- **Priority:** Must.
- **Acceptance criteria:** Hospital users cannot administer accounts or access incidents outside scope; data minimization is applied; updates are auditable.

## FR-013 — Provide Admin oversight

- **Description:** Admin users shall view system-level operational summaries and perform authorized user, incident review, and assignment actions.
- **Actor:** ADMIN.
- **Preconditions:** User is authenticated and has the relevant permission.
- **Main flow:** Admin reviews authorized summaries; takes a permitted action; backend validates, records, and audits the action.
- **Alternative flow:** Restricted evidence or unsupported action is denied; system failures are surfaced without leaking sensitive data.
- **Postconditions:** Administrative actions and resulting state are traceable.
- **Priority:** Must.
- **Acceptance criteria:** Admin actions are checked server-side and audited; oversight does not imply emergency dispatch capability.

## FR-014 — View incident history

- **Description:** Authorized users shall retrieve a scoped history of incident state changes and response activity.
- **Actor:** ADMIN, POLICE, HOSPITAL according to scope.
- **Preconditions:** User is authenticated and authorized for the incident.
- **Main flow:** Client requests history; backend filters by permission; client displays ordered events and actor attribution where permitted.
- **Alternative flow:** Out-of-scope access is denied; missing history is represented without inventing events.
- **Postconditions:** History remains read-only to ordinary users.
- **Priority:** Should.
- **Acceptance criteria:** History entries are ordered by recorded time and cannot be altered through ordinary client operations.

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

## Related Workflows

See [system workflow](../workflows/system_workflow.md), [AI detection workflow](../workflows/ai_detection_workflow.md), [incident response workflow](../workflows/incident_response_workflow.md), [user-role workflows](../workflows/user_role_workflows.md), and [requirements traceability](requirements_traceability.md).
