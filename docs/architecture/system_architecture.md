# System Architecture

**Status:** Proposed high-level architecture for team review. No services or production integrations are implemented.

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
    Owner[Video source owner/operator] -->|approved video and policy| AI[AI detection service]
    AI -->|authenticated candidate evidence; future contract| API[Django REST backend]
    Admin[Admin user] -->|authenticated client requests| Mobile[Flutter mobile app]
    Police[Police user] -->|authenticated client requests| Mobile
    Hospital[Hospital user] -->|authenticated client requests| Mobile
    Mobile -->|role-scoped API operations| API
    API -->|authoritative structured records| DB[(PostgreSQL)]
    API -->|restricted media access| Store[(Object storage; provider TBD)]
    API -->|simulated notifications only| Notify[Notification component]
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
        Notify[Notification simulation component]
    end
    subgraph Data[Data boundary]
        DB[(PostgreSQL structured records)]
        Store[(Object storage for media; TBD)]
    end
    Mobile -->|authenticated role-scoped API| API
    AI -->|authenticated candidate submission| API
    API --> DB
    API -->|authorized media access| Store
    API --> Notify
~~~

## High-Level Containers and Responsibilities

| Container | Owns or provides | Does not own |
|---|---|---|
| Flutter mobile app | Role-aware screens, client-side input, presentation of scoped incidents and simulated status | Authorization decisions, database access, verification authority |
| Django REST backend | Authentication, authorization, incident lifecycle, assignments, evidence metadata, audit, notification coordination, API boundary | Video model inference or raw media as its structured system of record |
| AI detection service | Input validation, preprocessing, detection/tracking, candidate evidence, temporal-analysis results | User permissions, authoritative response state, emergency dispatch |
| PostgreSQL | Users/role references, incident and response state, evidence metadata, notification records, audit records | Evidence media files or direct access for mobile clients |
| Object storage | Future media objects and controlled retrieval | Incident lifecycle or authorization policy; backend remains policy authority |
| Notification component | Prototype notification records and simulated outcomes; later provider adapter if approved | Real emergency dispatch in the academic prototype |

## Communication Flows

1. Approved input reaches the AI service through a video-ingestion mechanism that remains TBD.
2. The AI service submits candidate evidence to the backend over an authenticated service boundary. Contract shape, retries, and idempotency details require later agreement.
3. The backend validates the caller and candidate, records a DETECTED item, and manages verification and incident transitions.
4. The backend alone authorizes client operations and persists structured state in PostgreSQL.
5. Evidence is stored outside the public repository and accessed only through a controlled backend-authorized path.
6. The backend may create simulated notification records. The prototype sends no emergency alert or dispatch request.

### External Integration View

~~~mermaid
flowchart LR
    Source[Approved video source] -->|input mechanism TBD| AI[AI service]
    AI -->|candidate event; future authenticated contract| API[Backend]
    API -->|private media access; provider TBD| Storage[Object storage]
    API -.->|simulated only in prototype| FCM[Push provider; no live delivery]
    Mobile[Flutter client] -.->|optional location display; provider TBD| Maps[Maps provider]
    API --> DB[(PostgreSQL)]
~~~

The dashed provider paths represent planned or optional boundaries, not active integrations. The maps provider and live push configuration are not selected or enabled.

## Data Ownership

- Backend: user identity, role assignments, incident state, assignment, response updates, notification status, and audit history.
- AI service: transient processing state and generated candidate evidence until successful submission; exact retention and deletion are TBD.
- PostgreSQL: structured data and media metadata, not video/image objects.
- Object storage: media objects under an approved retention and access policy; provider TBD.
- Mobile client: no authoritative copy; local cache lifetime and sensitive-data protection are implementation decisions.

## Failure Handling

- Invalid or unauthorized input is rejected and distinguished from a completed analysis with no candidate.
- AI timeout or model failure does not produce a verified incident.
- Backend unavailability requires retry behavior that avoids unintended duplicate incidents; exact idempotency contract is TBD.
- Missing evidence or map/notification provider failure is surfaced as unavailable and does not erase the incident record.
- Database failure must not be reported to a caller as a successful state change.
- Notification simulation failure is recorded; it never falls back to a real emergency channel.

## Security Boundaries

Trust boundaries exist between source owners and AI processing, AI service and backend, mobile clients and backend, backend and database, and backend and media/notification providers. The backend validates identity and object-level permission at each protected operation. See [trust boundaries](trust_boundaries.md) for threats and controls.

## Scalability and Trade-offs

Separating AI processing from backend transactions allows the two workloads to evolve and fail independently, but introduces service identity, event delivery, retry, deduplication, and observability requirements. Separating media from relational data supports different retention and access controls, but adds storage-provider and signed-access decisions. Numeric throughput, latency, concurrency, and availability goals remain TBD until workload and deployment assumptions are approved.

## Confirmed Direction and Open Decisions

The planned stack is Flutter/Dart, Python/Django REST Framework, PostgreSQL, and Python computer-vision tooling using YOLO/OpenCV/PyTorch/NumPy. These are planned technologies, not proof of implementation or final version selection. Object storage, maps, model/version, tracking, verification method, input mechanism, service communication, deployment, notification delivery, Flutter state management, and background processing remain open. See [technology decisions](technology_decisions.md) and [open architecture decisions](open_architecture_decisions.md).
