# Data Flow

**Status:** REVISED_DRAFT — pending team approval. Conceptual flows only; not API, schema, or provider contracts.

## Video Source Ingestion

~~~mermaid
flowchart TD
    Owner[Source owner/operator] --> Register[Register/configure VideoSource]
    Register --> Auth{Ownership and processing permission validated?}
    Auth -- No --> Deny[Keep unauthorized; record review outcome]
    Auth -- Yes --> Enabled[VideoSource authorized under policy]
    File[Controlled approved demo file] --> Enabled
    Enabled --> Input[Receive file or replaceable stream input]
    Input --> Provenance[Bind source identity and timestamp provenance]
    Provenance --> AI[AI processing]
    AI --> Event[Create one or more DetectionEvents]
    Event --> Backend[Submit authenticated event to backend]
~~~

The source registry stores references/configuration metadata only. Camera credentials belong in protected runtime configuration, never documentation or Git. File ingestion remains supported for demonstrations; RTSP/streaming is not selected.

## DetectionEvent to Candidate Association

~~~mermaid
flowchart TD
    AI[AI service] --> Submit[Submit DetectionEvent with event identity and provenance]
    Submit --> Auth{AI_SERVICE identity and permission valid?}
    Auth -- No --> Reject[Reject submission; audit security outcome]
    Auth -- Yes --> Integrity{Source authorized and payload valid?}
    Integrity -- No --> RejectEvent[Reject/quarantine event; no candidate/incident]
    Integrity -- Yes --> Duplicate{Same event identity seen before?}
    Duplicate -- Yes --> Idempotent[Return/link prior intake outcome]
    Duplicate -- No --> StoreEvent[Persist distinct DetectionEvent]
    StoreEvent --> Match{Related to existing AccidentCandidate?}
    Match -- Confident match --> Associate[Associate event; preserve individual provenance]
    Match -- Uncertain --> Review[Flag possible duplicate for human review]
    Match -- No --> NewCandidate[Create AccidentCandidate RECEIVED]
    Associate --> Candidate[Candidate UNDER_REVIEW]
    NewCandidate --> Candidate
    Review --> Candidate
~~~

Event-level idempotency and candidate-level duplicate association are separate controls. Same event identity is safely repeatable; different observations may contribute to one candidate. Similarity rules are not approved; uncertain association is reviewed, not silently merged or discarded.

## Candidate Verification and Incident Creation

~~~mermaid
sequenceDiagram
    actor Reviewer as Authorized human reviewer
    participant App as Flutter client
    participant API as Backend
    participant DB as PostgreSQL
    API->>DB: Record candidate RECEIVED and related DetectionEvents
    API->>DB: Set candidate UNDER_REVIEW
    Reviewer->>App: Review permitted evidence and uncertainty
    App->>API: Submit verify/reject decision with rationale
    API->>API: Check human identity, object scope, role, and transition
    alt Rejected
        API->>DB: Record candidate REJECTED and AuditEvent
        Note over DB: No AccidentIncident is created
    else Verified
        API->>DB: One transaction: set candidate VERIFIED, create linked OPEN AccidentIncident, append histories/audit
        Note over DB: Transaction failure leaves no orphan incident or falsely verified candidate
    end
~~~

The authoritative incident is created by the backend only after authorized human verification. The verification actor/role is pending team approval. Rejected candidates remain distinct for audit/evaluation under the approved retention policy.

## End-to-End Multi-Agency Data Flow

~~~mermaid
sequenceDiagram
    actor Owner as Source owner/operator
    participant AI as AI service
    participant API as Backend
    participant DB as PostgreSQL
    actor Reviewer as Authorized reviewer
    actor Police as POLICE user
    actor Hospital as HOSPITAL user
    Owner->>AI: Supply authorized VideoSource input
    AI->>AI: Validate source; analyze frames and temporal evidence
    AI->>API: Submit machine-authenticated DetectionEvent(s)
    API->>DB: Deduplicate event identity; associate/create AccidentCandidate
    Reviewer->>API: Verify or reject candidate
    alt Rejected
        API->>DB: Record REJECTED candidate and audit; no incident
    else Verified
        API->>DB: Atomically create linked OPEN AccidentIncident
        API->>DB: Create independent Police and/or Hospital assignments
        API->>Police: Create simulated notification record
        API->>Hospital: Create simulated notification record
        Police->>API: Acknowledge/update own assignment
        Hospital->>API: Independently acknowledge/update own assignment
        API->>DB: Record separate assignment histories and Responses
    end
~~~

Assignment state is never copied to the other agency or treated as an incident acknowledgement. Notification state does not drive either assignment. All arrows to Police/Hospital represent prototype simulation only.

## Evidence Upload Sequence

~~~mermaid
sequenceDiagram
    participant AI as AI service
    participant API as Backend authorization service
    participant Store as Private object storage (provider TBD)
    participant DB as PostgreSQL metadata
    AI->>API: Submit DetectionEvent/evidence metadata and request upload authorization
    API->>API: Authenticate AI_SERVICE; verify candidate and scoped upload permission
    API->>DB: Create EvidenceAsset PENDING_UPLOAD with server-controlled object reference
    API-->>AI: Return short-lived, single-object, operation-scoped authorization (preferred)
    AI->>Store: Upload only authorized object
    Store-->>AI: Upload result and integrity metadata
    AI->>API: Report completion using authorized reference
    API->>DB: Set QUARANTINED; append completion AuditEvent
    API->>Store: Verify object identity, size/type, checksum/integrity where supported
    alt Required validation/scanning succeeds
        API->>DB: Set AVAILABLE; append AuditEvent
    else Validation fails
        API->>DB: Set FAILED; deny retrieval and append AuditEvent
    end
~~~

If a selected provider cannot support scoped direct upload, use backend-mediated upload as the documented fallback; this trades additional backend bandwidth for simpler transfer control. Provider, media size/type limits, checksum method, and scanning implementation are pending decisions.

## Evidence Retrieval Sequence

~~~mermaid
sequenceDiagram
    actor User as Authorized ADMIN/POLICE/HOSPITAL user
    participant App as Flutter client
    participant API as Backend authorization service
    participant DB as PostgreSQL metadata
    participant Store as Private object storage (provider TBD)
    User->>App: Request evidence for candidate/incident
    App->>API: Request by logical EvidenceAsset reference
    API->>DB: Load evidence state and candidate/incident/assignment relationships
    API->>API: Check user, role, assignment/object scope, and AVAILABLE state
    alt Denied or unavailable
        API-->>App: Safe denial/unavailable outcome; record sensitive access attempt
    else Authorized
        API->>Store: Create restricted short-lived retrieval or stream through backend
        Store-->>App: Media via authorized path
        API->>DB: Append sensitive retrieval AuditEvent
    end
~~~

No mobile client receives broad storage credentials or selects an arbitrary object path. Evidence retrieval is separately audited; data minimization may further restrict Hospital access.

## Location Provenance Flow

~~~mermaid
flowchart LR
    Source[VideoSource registry] --> CameraLoc[Registered camera location]
    GPS[Approved GPS metadata] --> Claim[Location claim]
    Manual[Authorized manual verification/correction] --> Claim
    CameraLoc --> Claim
    Event[DetectionEvent source/time] --> Claim
    Claim --> Prov[LocationProvenance: source, timestamp, uncertainty, verification]
    Prov --> Candidate[AccidentCandidate location context]
    Candidate -->|verified candidate; preserve origin| Incident[AccidentIncident location claim]
    Incident --> UI[Authorized scoped display with uncertainty]
~~~

Camera coordinates indicate the camera location, not automatically the accident location. GPS or inferred locations retain their method and timestamp. Manual corrections require an authorized actor and correction history. Missing or uncertain location stays explicitly unknown/imprecise; precision is never fabricated.

## Data Concepts, Ownership, and Consistency

| Concept | Authoritative owner | Relationship and handling |
|---|---|---|
| VideoSource | Backend registry metadata; source owner owns source | Authorization, source identity/type, location reference, availability/health, timestamp provenance, input configuration reference, processing/retention policy reference |
| DetectionEvent | Backend intake after AI submission | One machine observation and submission outcome; associated to zero/one candidate; repeated IDs are idempotent |
| AccidentCandidate | Backend | Has one or more related DetectionEvents and EvidenceAssets; may be verified/rejected; only verified candidate can create incident |
| AccidentIncident | Backend | Created once from verified candidate; owns incident lifecycle/history, not individual agency acknowledgement |
| EvidenceAsset | Backend metadata/lifecycle; object storage media bytes | May be linked to candidate and referenced by incident; states PENDING_UPLOAD, UPLOADING, QUARANTINED, AVAILABLE, FAILED, EXPIRED, DELETED |
| ResponseAssignment | Backend | One verified incident to one eligible Police/Hospital target; one incident may have multiple independent assignments |
| Response | Backend | One activity/status update stream associated with one assignment; agency updates never overwrite each other |
| IncidentStatusHistory | Backend | Append-oriented incident transitions |
| AssignmentStatusHistory | Backend | Append-oriented state and reassignment/cancellation events per assignment |
| Notification | Backend | Independent delivery/read simulation; creation/read is not assignment acknowledgement |
| LocationProvenance | Backend | Origin, associated source, timestamp, accuracy/uncertainty, verification state, and correction history |
| AuditEvent | Backend | Actor/service, time, target/action/outcome, and safe metadata; secrets and raw media excluded |

## Conceptual State Transition Rules

| Concept | Proposed transitions | Authority and safeguards |
|---|---|---|
| DetectionEvent intake outcome | RECEIVED -> ACCEPTED, REJECTED, or DUPLICATE_RESULT; processing outcome is separately SUCCESS, NO_OBSERVATION, UNCERTAIN, or FAILED | Backend assigns intake outcome after machine/source/payload validation; repeated stable identity returns the prior outcome |
| AccidentCandidate | RECEIVED -> UNDER_REVIEW -> VERIFIED or REJECTED | Backend accepts event association; only authorized human may verify/reject; AI_SERVICE cannot make either transition |
| AccidentIncident | OPEN -> RESPONSE_ACTIVE -> RESOLVED -> CLOSED; OPEN may reach RESOLVED if an authorized reviewer records a no-response outcome | Backend owns state; RESOLVED and CLOSED require separate authorized decisions/reasons; reopen remains denied pending policy |
| ResponseAssignment | PENDING -> ACKNOWLEDGED -> IN_PROGRESS -> COMPLETED; PENDING/ACKNOWLEDGED/IN_PROGRESS may also move to UNABLE_TO_RESPOND or CANCELLED; PENDING -> EXPIRED only under approved timeout policy | Target user changes only own assignment; cancellation/reassignment preserves prior history and creates a new record |
| Notification | CREATED -> PENDING -> DELIVERED_SIMULATED or FAILED; delivered may become READ; permitted states may become CANCELLED; FAILED may retry to PENDING under policy | Backend owns delivery simulation; read/delivery never acknowledges an assignment; no external emergency channel |
| EvidenceAsset | PENDING_UPLOAD -> UPLOADING -> QUARANTINED -> AVAILABLE; upload/validation may reach FAILED; retention may transition AVAILABLE -> EXPIRED -> DELETED | Backend owns metadata and transition authority; only AVAILABLE can be retrieved; expiry/deletion blocks retrieval; retry requires new scoped upload authorization |
| VideoSource authorization | Illustrative: PENDING_REVIEW -> AUTHORIZED -> SUSPENDED or REVOKED; SUSPENDED may return to AUTHORIZED after review | Registry owner/authorization policy is TBD; only AUTHORIZED sources may produce accepted events; revocation blocks new processing |

PostgreSQL stores structured records and references, never evidence media bytes. Object storage owns media bytes only; the backend is always the authorization authority.

## Failure, Retry, and Audit Outcomes

| Scenario/trigger | Expected behavior and data consistency | Audit and user-visible outcome | Retry/manual recovery and approval |
|---|---|---|---|
| Invalid AI_SERVICE credentials or replay | Reject before event/evidence mutation; no candidate or incident created | Record service identity/outcome without credential; safe submission denial | Correct credentials and retry; auth mechanism/rotation policy approval pending |
| Unauthorized/revoked VideoSource | Do not process input or accept resulting event; preserve source authorization state | Record source reference and denial; show source unavailable to authorized operator | Owner/admin reviews authorization; registration authority policy pending |
| Duplicate DetectionEvent ID | Return prior intake result; do not create second event/candidate/assignment | Append/reuse idempotent receipt/audit reference; caller sees duplicate-safe result | Retry with same ID after unknown outcome; idempotency contract pending |
| Multiple distinct events may share candidate | Preserve each event; associate only under approved rule | Record association decision/provenance; possible duplicate appears for review | Authorized reviewer resolves uncertain association; grouping policy pending |
| Candidate rejected | Retain candidate and related events/evidence references; create no AccidentIncident | Record reviewer, rationale, time; candidate displays REJECTED | Correction/reopen policy and retention period pending |
| Verification unavailable/fails | Candidate remains UNDER_REVIEW; no incident created | Record failure/timeout and reviewer-visible pending status | Retry/manual review; reviewer authority and SLA pending |
| Evidence upload fails | Asset remains PENDING_UPLOAD or FAILED; never AVAILABLE; candidate/incident state remains intact | Record transfer outcome; reviewer sees media unavailable | Retry with new scoped authorization or backend-mediated fallback; retry window/limits pending |
| Evidence integrity/type/size validation fails | Asset remains QUARANTINED or becomes FAILED; no retrieval; candidate/incident state remains intact | Record validation reason without exposing media; show unavailable state | Reupload/manual review under approved policy; checksum/scanning requirements pending |
| Object storage unavailable | Asset remains unavailable and metadata stays consistent; candidate/incident state is not created/erased by storage failure | Record provider failure; authorized reviewer sees evidence unavailable | Retry/reconcile when provider returns; provider and retry policy pending |
| Evidence access denied | Do not issue retrieval authorization or reveal object existence | Record sensitive access attempt; client gets safe denial | User requests appropriate assignment; scope policy pending |
| Backend unavailable during event submission | Caller cannot assume success; retry same event identity; backend deduplicates after recovery | Record when received; service reports pending/unknown | Backoff/manual reconciliation; retry window pending |
| Database transaction failure during verification/incident creation | Candidate and linked incident/history/audit commit atomically; no orphan incident or false VERIFIED state | Return safe failure; operations log correlated non-sensitive failure | Retry same decision idempotently or manual review; transaction design future |
| Police assignment not acknowledged | Police assignment remains PENDING/overdue; no shared incident ACK state | Record assignment/notification status; Admin sees overdue indicator | Proposed default is manual follow-up; timeout policy pending |
| Hospital assignment not acknowledged | Hospital assignment independently remains PENDING/overdue | Record separately; no effect on Police assignment | Manual follow-up; timeout policy pending |
| One agency acknowledges while other remains pending | Only acknowledging assignment becomes ACKNOWLEDGED; the other remains PENDING | Separate histories and UI states | Continue manual follow-up for pending assignment |
| Agency unable to respond | That assignment becomes UNABLE_TO_RESPOND with reason; other assignments are unchanged | Record actor, reason, time; show Admin review outcome | Admin may create replacement assignment under policy; assignment authority pending |
| Assignment cancellation | Mark only that assignment CANCELLED; preserve its history; incident and other targets unchanged | Record actor/reason/time; show cancelled target | Authorized cancellation actor/policy pending |
| Assignment reassignment | Cancel/supersede old assignment and create a new PENDING assignment for selected target | Audit old/new target and link histories; simulated notification is separate | Authorized assignment actor; target eligibility policy pending |
| Partial response completion | One assignment may be COMPLETED while another remains active/unable/pending; incident does not inherit completion | Display each agency independently | Incident resolution waits for terminal assignment handling under proposed rule |
| Incident resolution with outstanding assignments | Reject RESOLVED while any assignment is nonterminal; require authorized terminal action or documented override policy | Safe transition error and audit attempt | Resolve assignments first; override policy pending |
| Unauthorized incident closure | Deny; incident remains RESOLVED or current state | Audit attempted closure; safe denial | Authorized closure reviewer may retry; authority pending |
| Duplicate/corrected incident | Do not silently merge/delete; preserve links and history; correction creates attributable audit/history entry | Authorized reviewer sees duplicate/correction relation | Manual review; merge/correction policy pending |
| Incident reopening | Default deny until policy approved; if approved, create explicit reopening transition/history | Audit actor, reason, prior state | Authorized Admin/reviewer only under approved policy |
| Notification simulation failure | Notification becomes FAILED; incident/assignment state is unchanged | Label failure as simulated; no dispatch implication | Retry only under simulation policy; never contact real agency |
| Missing/uncertain location | Preserve unknown/uncertainty and source provenance; do not fabricate accident coordinates | UI shows camera vs inferred/manual source and uncertainty | Authorized manual correction with history; location policy pending |
| VideoSource unavailable | No analysis or candidate; source health/failure separate from no-candidate | Record source and time outcome; operator sees unavailable | Retry/review source; health/stream policy pending |

## Future Contracts and Limits

These diagrams define conceptual direction only. API endpoints, event schemas, database columns/types, object-store provider, concrete security mechanism, retention durations, upload size limits, timeout intervals, and legal obligations require later approval. No real notification or emergency dispatch is possible in the prototype.
