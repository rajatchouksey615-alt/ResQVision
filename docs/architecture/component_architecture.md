# Component Architecture

**Status:** Proposed component boundaries for team review; no application services are implemented.

## Component View

~~~mermaid
flowchart LR
    User[Admin, Police, Hospital] --> Mobile[Flutter application]
    Mobile -->|authenticated API| API[Django REST backend]
    AI[AI detection service] -->|candidate evidence only| API
    API --> Identity[Identity and access control]
    API --> Incident[Incident lifecycle and assignment]
    API --> Evidence[Evidence metadata and access coordination]
    API --> Audit[Audit and notification records]
    Identity --> DB[(PostgreSQL)]
    Incident --> DB
    Evidence --> DB
    Evidence --> Store[(Object storage; provider TBD)]
    Audit --> DB
~~~

## Flutter Mobile Application

- Provides authentication UI, role-aware navigation, dashboards, incident lists/details, permitted evidence display, optional maps, simulated notifications, and response/readiness updates.
- Calls backend capabilities through an authenticated client boundary and presents loading, empty, uncertainty, unavailable, and error states.
- Stores no authoritative incident state and does not enforce access by hiding screens alone.

## Django REST Backend

- Owns identity, authorization, user/role administration, incident lifecycle, verification decisions recorded by authorized actors, assignment, response state, evidence metadata, notifications, and audit history.
- Exposes the future API boundary and validates role and object-level scope for every operation.
- Keeps domain rules independent from transport/view code and coordinates PostgreSQL and media access.
- Does not perform model inference or contact emergency services.

## AI Detection Service

- Validates permitted video input, preprocesses frames, performs selected detection and tracking, evaluates candidate evidence over time, and creates evidence references.
- Preserves provenance, timing, uncertainty, and failure outcomes.
- Submits candidates through a service-authenticated interface. It cannot administer users, confirm an incident on its own, change response status, assign responders, or dispatch services.

## PostgreSQL

Stores backend-owned structured records: identity/role references, incident and response state, evidence metadata, notification records, and audit history. Exact entities and schema are deferred to database design.

## Object Storage

Will hold actual image/video evidence after provider, access method, retention, encryption, and deletion policy are approved. PostgreSQL stores references and metadata, not media payloads.

## Notification Component

Coordinates notification records and simulated delivery outcomes. Firebase Cloud Messaging is planned but has no live configuration; prototype flows must not send real emergency alerts. Retry and delivery semantics remain TBD.

## Infrastructure and Operations

Future local development and deployment configuration will support isolated services, secret management, health signals, logs, and backups. No Docker services, cloud resources, or monitoring systems are configured. Hosting, operational ownership, and recovery objectives remain TBD.

## Cross-Component Contracts

Before implementation, owners must agree on service identity, API/event versioning, role semantics, candidate and verification states, evidence references, safe errors, retry/idempotency behavior, retention, and compatibility. Document approved API contracts under docs/api_documentation/. This design does not define endpoint names or request/response schemas.
