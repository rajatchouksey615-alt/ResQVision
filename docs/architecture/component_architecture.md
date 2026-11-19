# Component Architecture

**Documentation status:** REVISED_DRAFT — pending team approval. Internal Django domain services, selected authenticated REST endpoints, and the Flutter incident read experience are implemented. Candidate, evidence, location, and incident-lifecycle routes remain policy-blocked; external production integrations are not enabled.

## Component Relationship

~~~mermaid
flowchart LR
    User[ADMIN / POLICE / HOSPITAL] --> Mobile[Flutter mobile application]
    Mobile -->|authenticated, object-scoped API| API[Django REST backend]
    AI[AI detection service] -->|machine-authenticated DetectionEvents| Intake[DetectionEvent intake]
    Intake --> Candidate[AccidentCandidate service]
    Reviewer[Authorized human reviewer] -->|verify or reject| Candidate
    Candidate -->|verified only| Incident[AccidentIncident service]
    Incident --> Assign[ResponseAssignment service]
    Assign --> Response[Per-assignment Response]
    API --> Evidence[EvidenceAsset authorization and lifecycle]
    AI -->|request scoped upload authorization and report completion| Evidence
    Evidence -->|short-lived single-object authorization| AI
    AI -->|direct transfer where supported| Store[(Object storage; provider TBD)]
    Evidence -->|mediated-upload fallback and controlled retrieval| Store
    Candidate --> DB[(PostgreSQL structured state and histories)]
    Incident --> DB
    Assign --> DB
    Response --> DB
    Evidence --> DB
    API --> Audit[AuditEvent and Notification services]
    Audit --> DB
~~~

## Flutter Mobile Application

- Provides authentication UI, role-aware navigation, candidate review where authorized, incident lists/details, assigned-agency dashboards, permitted EvidenceAsset retrieval, provenance-aware location display, simulated Notification state, and assignment response/readiness updates.
- Treats Police and Hospital assignments as separate records with independent acknowledgement, progress, completion, unable-to-respond, cancellation, and approved expiration states.
- Presents loading, empty, uncertain, unavailable, rejected, and error states accurately.
- Stores no authoritative workflow state. Backend authorization is required for every operation; route hiding is supplementary only.

## Django REST Backend

- **Identity/access:** Owns human users, ADMIN/POLICE/HOSPITAL roles, separate AI_SERVICE machine identity, token/service permissions, and object-level authorization.
- **Video source registry:** Owns source registration/authorization metadata, availability/health information, and processing-policy references; source ownership itself remains with its owner.
- **Event intake:** Authenticates AI_SERVICE, validates DetectionEvent provenance and submission outcome, supports idempotent event retries, and associates multiple events to an AccidentCandidate without losing event identity.
- **Candidate review:** Owns candidate state (RECEIVED, UNDER_REVIEW, VERIFIED, REJECTED), review decisions, reviewer attribution, and candidate-to-event/evidence provenance. AI_SERVICE cannot verify/reject.
- **Incident management:** Creates one authoritative AccidentIncident only after an authorized verification decision; owns incident state (OPEN, RESPONSE_ACTIVE, RESOLVED, CLOSED) and IncidentStatusHistory.
- **Assignments and responses:** Creates one ResponseAssignment per eligible target; maintains independent assignment state/history and Response activity. Reassignment cancels the old assignment and creates a new linked assignment; it does not overwrite history.
- **Evidence coordination:** Owns EvidenceAsset metadata, upload authorization, validation/quarantine outcome, availability, retrieval authorization, retention/deletion actions, and audit. It never delegates business authorization to object storage.
- **Location provenance:** Records source, timestamp, uncertainty, verification, and correction references; distinguishes camera position from inferred or manually verified incident location.
- **Notifications/audit:** Owns Notification records and delivery state separately from assignments; records attributable security and lifecycle events.

## AI Detection Service

- Processes only an authorized VideoSource or controlled approved file, preserving source identity and timing provenance.
- Produces DetectionEvents, temporal analysis, uncertainty, and EvidenceAsset metadata.
- Uses a separate AI_SERVICE identity. It may submit events, request narrowly scoped evidence upload authorization, upload only the authorized object, and report completion.
- It cannot verify or reject AccidentCandidates, create/update AccidentIncidents, create assignments, acknowledge or resolve a response, administer human users, retrieve unrelated evidence, or dispatch responders.
- Input ingestion, model/version, tracking, event identity contract, and evidence transfer implementation remain pending decisions.

## PostgreSQL

Stores backend-owned structured records and metadata for users/roles, VideoSources, DetectionEvents, AccidentCandidates, AccidentIncidents, ResponseAssignments, Responses, separate status histories, EvidenceAssets, LocationProvenance, Notifications, and AuditEvents. This is a conceptual inventory only; no physical entities, fields, types, constraints, or migrations are approved here.

## Object Storage

Stores media bytes only. Preferred flow is backend-authorized short-lived, single-object, operation-scoped upload/retrieval where supported. The backend validates object identity, type/size, and integrity where available and confirms required scanning before an asset becomes AVAILABLE; backend authorization controls each read. Backend-mediated upload is a local-development or provider fallback. No public bucket, long-lived broad credential, or client-controlled object path is allowed.

## Notification Component

Maintains independent states CREATED, PENDING, DELIVERED_SIMULATED, FAILED, READ, and CANCELLED for prototype notification records. Notification creation/delivery/read never means a Police/Hospital assignment was acknowledged. Firebase Cloud Messaging is planned but no live delivery is configured.

## Infrastructure and Operations

Future local development and deployment support will need private media configuration, secret management, service identity, logs/health, database backups, retention/deletion, and recovery procedures. No Docker services, cloud resources, or monitoring systems are configured. Timeout policies must never trigger external emergency escalation.

## Cross-Component Contracts

Before implementation, agree on versioned DetectionEvent identity/provenance, candidate association and duplicate rules, candidate review authority, incident creation transaction semantics, assignment target/scope and independent transitions, EvidenceAsset authorization/completion/integrity behavior, VideoSource authorization, LocationProvenance, safe errors, retry semantics, and retention. This design does not define endpoints, request/response schemas, or physical database structure.
