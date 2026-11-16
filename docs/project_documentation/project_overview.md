# Project Overview

**Status:** REVISED_DRAFT — pending team approval.

ResQVision (AI-Based Road Accident Detection and Emergency Response System) is an academic major project for a team of four. It explores a modular system that analyzes authorized CCTV/video sources, submits AI DetectionEvents, associates them with AccidentCandidates, and creates authoritative AccidentIncidents only after authorized human verification. Role-based users review incidents and manage independent Police and Hospital ResponseAssignments with simulated responses.

The project is in **Phase 3 — Domain Services and Business Logic**. The revised Phase 1 specification remains pending team approval. Django models, migrations, and internal domain services for the local PostgreSQL schema are implemented; the Flutter/Dart app, API endpoints, Python AI service, object-storage integration, and deployment infrastructure remain unimplemented.

The prototype will not send real emergency alerts, dispatch ambulances, or integrate with emergency organizations. Detection is not confirmation; candidates require authorized human verification. Evidence remains private and backend-authorized, and location claims retain source and uncertainty provenance. Map, object storage, deployment, model, and other provider choices remain pending.

See the [system requirements specification](../requirements/system_requirements_specification.md), [system architecture](../architecture/system_architecture.md), and [open architecture decisions](../architecture/open_architecture_decisions.md).
