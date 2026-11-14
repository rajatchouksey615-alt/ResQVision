# System Architecture

**Status:** REVISED_DRAFT — pending team approval. No services or production integrations are implemented.

## Architecture Goals

- Keep mobile, backend, AI processing, structured data, media, and notification responsibilities separate.
- Make the backend the single source of truth for identities, authorization, incident state, and audit history.
- Keep AI candidate evidence separate from authoritative human verification and response decisions.
- Isolate failures and preserve traceability across processing and incident workflows.
- Minimize and protect sensitive video, evidence, location, identity, and incident data.
- Avoid coupling the design to providers or contracts that have not been selected.

## System Context

~~~mermaid
flowchart LR
    Owner[Video source owner/operator] -->|registered and authorized source| Registry[VideoSource management]
    Registry -->|input and source/time provenance| AI[AI detection service]
    AI -->|authenticated DetectionEvents and evidence metadata| API[Django REST backend]
    API --> Candidate[AccidentCandidate]
    Reviewer[Authorized human reviewer] -->|verify or reject| API
    API -->|verified candidate creates incident| Incident[AccidentIncident]
    Incident --> PoliceAssign[Police ResponseAssignment]
    Incident --> HospitalAssign[Hospital ResponseAssignment]
    PoliceAssign -->|independent Response updates| API
    HospitalAssign -->|independent Response updates| API
    Admin[Admin user] -->|authenticated client requests| Mobile[Flutter mobile app]
    PoliceUser[Police user] -->|authenticated client requests| Mobile
    HospitalUser[Hospital user] -->|authenticated client requests| Mobile
    Mobile -->|role-scoped API operations| API
    API -->|authoritative structured records| DB[(PostgreSQL)]
    API -->|short-lived scoped upload authorization| AI
    AI -->|single-object upload where supported| Store[(Object storage; provider TBD)]
    API -->|mediated-upload fallback and controlled retrieval| Store
    API -->|separate simulated delivery state| Notify[Notification component]
    API -.->|optional map display; provider TBD| Maps[Maps provider]
~~~

## High-Level Container View

~~~mermaid
flowchart TB
    subgraph Client[Client boundary]
        Mobile[Flutter mobile application]
    end
    subgraph Services[Application service boundary]
        API[Django REST backend]
        AI[Independent AI detection service]
        Domain[Event, candidate, incident and assignment services]
        Notify[Notification simulation component]
    end
    subgraph Data[Data boundary]
        DB[(PostgreSQL structured records)]
        Store[(Object storage for media; TBD)]
    end
    Mobile -->|authenticated role-scoped API| API
    AI -->|authenticated DetectionEvent submission| API
    API --> Domain
    Domain -->|candidate and incident state| DB
    Domain -->|assignment/response histories| DB
    API --> DB
    API -->|authorized media access| Store
    API --> Notify
~~~

## Logical Records and Ownership

| Concept | Owner and lifecycle |
|---|---|
| VideoSource | Backend-managed authorization, availability/health and provenance reference; external source owner retains source/media ownership |
| DetectionEvent | Backend accepts/rejects authenticated AI submission and stores provenance/outcome; each event remains distinct |
| AccidentCandidate | Backend creates/associates one or more related DetectionEvents; states are RECEIVED, UNDER_REVIEW, VERIFIED, REJECTED |
| AccidentIncident | Backend creates only after authorized candidate verification; separate OPEN, RESPONSE_ACTIVE, RESOLVED, CLOSED lifecycle |
| EvidenceAsset | Backend owns metadata, validation/access policy, lifecycle and audit; object storage owns bytes only |
| ResponseAssignment | One incident-to-one eligible agency target assignment; each assignment has independent status/history |
| Response | Activity/status records associated with exactly one assignment |
| IncidentStatusHistory / AssignmentStatusHistory | Backend-owned, append-oriented history of their respective lifecycle |
| Notification | Backend-owned delivery/read simulation; not a response acknowledgement or incident state |
| LocationProvenance | Backend retains source, timestamp, uncertainty/accuracy, verification and correction history for each location claim |

See [conceptual data design](../database_design/erd.md) for logical relationships. These are not approved tables or columns.

## High-Level Containers and Responsibilities

| Container | Owns or provides | Does not own |
|---|---|---|
| Flutter mobile app | Role-aware screens, client-side input, presentation of scoped incidents and simulated status | Authorization decisions, database access, verification authority |
| Django REST backend | Human/machine identity, event intake, candidate review, verified incident creation, independent assignments/responses, evidence lifecycle/access, notification and audit records | Video model inference or raw media as its structured system of record |
| AI detection service | Authorized-source processing, detection observations, candidate evidence, upload request/completion for its own evidence | Candidate verification/rejection, incident creation, user permissions, agency status, emergency dispatch |
| PostgreSQL | Video source metadata, event/candidate/incident references, independent assignment/response and histories, evidence metadata, notifications, audit | Evidence media bytes or direct mobile-client access |
| Object storage | Future media bytes and restricted object transfer | Business authorization, incident lifecycle, or public access policy |
| Notification component | Prototype notification records and simulated outcomes; later provider adapter if approved | Real emergency dispatch in the academic prototype |

## Communication Flows

1. A source owner/operator registers a VideoSource; an authorized source supplies controlled video with source and timestamp provenance.
2. The AI service validates the source and submits authenticated DetectionEvents. A stable event ID supports idempotent retries; candidate-level duplicate association is a separate policy.
3. The backend creates/associates an AccidentCandidate, preserving one-to-many event provenance. Uncertain grouping is flagged for review rather than silently merged.
4. An authorized human verifies/rejects the candidate. The backend transactionally records VERIFIED and creates one linked AccidentIncident only after verification.
5. The backend authorizes each Police/Hospital ResponseAssignment independently. Each acknowledgement and Response belongs to its assignment.
6. The AI service obtains a short-lived, object-scoped upload authorization where supported; the backend validates completion/integrity before EvidenceAsset becomes AVAILABLE. Backend-mediated upload is the fallback.
7. Mobile evidence retrieval is authorized by the backend per object and user/assignment scope; direct unrestricted object-store access is prohibited.
8. Incident, assignment, notification, and evidence lifecycle changes are separate and audited. Notifications remain simulated.

### External Integration View

~~~mermaid
flowchart LR
    Source[Approved video source] -->|input mechanism TBD| AI[AI service]
    AI -->|candidate event; future authenticated contract| API[Backend]
    API -->|short-lived scoped upload authorization| AI
    AI -->|single-object upload where supported| Storage[Object storage; provider TBD]
    API -->|mediated-upload fallback and controlled retrieval| Storage
    API -.->|simulated only in prototype| FCM[Push provider; no live delivery]
    Mobile[Flutter client] -.->|optional location display; provider TBD| Maps[Maps provider]
    API --> DB[(PostgreSQL)]
~~~

The dashed provider paths represent planned or optional boundaries, not active integrations. The maps provider and live push configuration are not selected or enabled.

## Data Ownership

- Backend: user/service identities, VideoSource authorization/health metadata, DetectionEvent intake, AccidentCandidate decisions, AccidentIncident, individual assignments/Responses, EvidenceAsset metadata/lifecycle, notification state, LocationProvenance, and audit history.
- AI service: transient processing observations and generated evidence until successful backend submission/upload completion; exact retention and deletion are TBD.
- PostgreSQL: structured data and media metadata, not video/image objects.
- Object storage: media bytes under an approved retention and access policy; provider TBD; it is not an authorization authority.
- Mobile client: no authoritative copy; local cache lifetime and sensitive-data protection are implementation decisions.

## Failure Handling

- Invalid or unauthorized input is rejected and distinguished from a completed analysis with no candidate.
- Invalid AI service identity is denied; it cannot create, verify, or mutate incident/assignment state.
- Repeated identical DetectionEvent IDs return/link to the original intake outcome; different events that may share a candidate are separately preserved and uncertain matches reviewed.
- AI timeout or model failure does not produce a verified incident.
- Backend unavailability during event intake returns an unaccepted/unknown outcome and the AI service retries with the same idempotency identity; no candidate/incident duplication is permitted.
- Evidence upload/integrity failure leaves the asset FAILED or QUARANTINED, never AVAILABLE; retry/manual recovery is audited.
- Object-store failure leaves metadata and business state consistent and evidence unavailable; it does not create or erase an incident.
- Incident creation and VERIFIED candidate linkage must commit atomically; transaction failure leaves the candidate reviewable and creates no orphan incident.
- Missing evidence, map, or notification provider failure is surfaced as unavailable and does not erase the incident record.
- Database failure must not be reported as a successful state change or partial transition.
- One agency's non-acknowledgement or unable-to-respond state never overwrites another assignment; overdue display/manual follow-up is the proposed default.
- Location gaps or uncertainty are explicit; camera position is not asserted as accident position.
- Notification simulation failure is recorded; it never falls back to a real emergency channel.

## Security Boundaries

Trust boundaries exist between source owner and VideoSource registry, source and AI processing, AI service and backend, mobile client and backend, backend and database, and backend and media/notification providers. Backend authorization controls every upload and retrieval; object storage cannot grant business access. See [trust boundaries](trust_boundaries.md) for threats and controls.

## Scalability and Trade-offs

Separating AI processing from backend transactions allows the two workloads to evolve and fail independently, but introduces service identity, event delivery, retry, deduplication, and observability requirements. Separating media from relational data supports different retention and access controls, but adds storage-provider and signed-access decisions. Numeric throughput, latency, concurrency, and availability goals remain TBD until workload and deployment assumptions are approved.

## Confirmed Direction and Open Decisions

The planned stack is Flutter/Dart, Python/Django REST Framework, PostgreSQL, and Python computer-vision tooling using YOLO/OpenCV/PyTorch/NumPy. These are planned technologies, not proof of implementation or final version selection. Object storage, maps, model/version, tracking, verification authority/method, input mechanism, service authentication, upload mechanism, timeout policy, deployment, notification delivery, Flutter state management, and background processing remain open. See [technology decisions](technology_decisions.md) and [open architecture decisions](open_architecture_decisions.md).
