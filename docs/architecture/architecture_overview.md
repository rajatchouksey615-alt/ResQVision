# Architecture Overview

**Status:** REVISED_DRAFT — pending team approval.

ResQVision is a modular system with an authenticated mobile client, a backend that owns candidate and incident decisions, an independent AI analysis service, PostgreSQL for structured records, and future object storage for evidence media. It distinguishes each AI DetectionEvent from its AccidentCandidate and any verified AccidentIncident, then tracks Police and Hospital ResponseAssignments independently.

## Context

~~~mermaid
flowchart LR
    Source[Authorized VideoSource] --> AI[AI analysis]
    AI -->|DetectionEvents and evidence metadata| Backend[Backend system of record]
    Backend --> Candidate[AccidentCandidate]
    Reviewer[Authorized human reviewer] -->|verify or reject| Backend
    Backend -->|verified candidate only| Incident[AccidentIncident]
    Incident --> Police[Police ResponseAssignment]
    Incident --> Hospital[Hospital ResponseAssignment]
    Police -->|independent Response history| Backend
    Hospital -->|independent Response history| Backend
    Admin[ADMIN] --> App[Flutter client]
    Police[POLICE] --> App
    Hospital[HOSPITAL] --> App
    App -->|authenticated, scoped operations| Backend
    Backend --> DB[(PostgreSQL)]
    Backend -->|short-lived object-scoped access| Media[(Object storage; TBD)]
    Backend --> Sim[Independent simulated Notification state]
~~~

## Core Decisions in the Design

- The backend is the only authority for access control, incident state, assignment, response status, and audit history.
- DetectionEvent, AccidentCandidate, AccidentIncident, ResponseAssignment, Response, EvidenceAsset, Notification, and their history records are distinct logical concepts.
- The backend validates events, associates multiple observations to a candidate, obtains human verification, and creates the authoritative incident only after verification.
- The AI service analyzes approved inputs and submits DetectionEvents/evidence. It cannot verify/reject a candidate, create an incident, or trigger response.
- Police and Hospital assignments, responses, and acknowledgements are independent; one agency's status is not copied to another or to the incident.
- The client communicates only with backend capabilities; it does not connect directly to PostgreSQL or object storage.
- PostgreSQL holds structured records and evidence metadata. Evidence files use a separately governed object-storage boundary; the backend owns authorization and the store owns bytes only.
- VideoSource authorization and LocationProvenance are preserved from input through event, candidate, and incident.
- Police and Hospital workflows model prototype coordination only. Notifications are simulated and real emergency integrations are disabled.
- Providers, model versions, thresholds, endpoint schemas, and operational targets remain TBD until reviewed.

See [system architecture](system_architecture.md), [component architecture](component_architecture.md), [trust boundaries](trust_boundaries.md), and [data flow](data_flow.md) for details.
