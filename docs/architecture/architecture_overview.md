# Architecture Overview

**Status:** Proposed overview for team review.

ResQVision is a modular system with an authenticated mobile client, a backend that owns user and incident state, an independent AI analysis service, PostgreSQL for structured data, and future object storage for evidence media. The architecture separates machine-generated candidate evidence from authorized verification and simulated response work.

## Context

~~~mermaid
flowchart LR
    Source[Approved video source] --> AI[AI analysis]
    AI -->|candidate and evidence reference| Backend[Backend system of record]
    Admin[ADMIN] --> App[Flutter client]
    Police[POLICE] --> App
    Hospital[HOSPITAL] --> App
    App -->|authenticated, scoped operations| Backend
    Backend --> DB[(PostgreSQL)]
    Backend --> Media[(Object storage; TBD)]
    Backend --> Sim[Simulated notifications]
~~~

## Core Decisions in the Design

- The backend is the only authority for access control, incident state, assignment, response status, and audit history.
- The AI service analyzes approved inputs and submits candidates. It cannot independently establish a real-world accident or trigger response.
- The client communicates only with backend capabilities; it does not connect directly to PostgreSQL or object storage.
- PostgreSQL holds structured records and media metadata. Evidence files use a separately governed object-storage boundary.
- Police and Hospital workflows model prototype coordination only. Notifications are simulated and real emergency integrations are disabled.
- Providers, model versions, thresholds, endpoint schemas, and operational targets remain TBD until reviewed.

See [system architecture](system_architecture.md), [component architecture](component_architecture.md), [trust boundaries](trust_boundaries.md), and [data flow](data_flow.md) for details.
