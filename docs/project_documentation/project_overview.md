# Project Overview

**Status:** REVISED_DRAFT — pending team approval.

ResQVision (AI-Based Road Accident Detection and Emergency Response System) is an academic major project for a team of four. It explores a modular system that analyzes authorized CCTV/video sources, submits AI DetectionEvents, associates them with AccidentCandidates, and creates authoritative AccidentIncidents only after authorized human verification. Role-based users review incidents and manage independent Police and Hospital ResponseAssignments with simulated responses.

The project is in **Phase 1 — Requirements Engineering and System Design**. This revised specification is pending team approval; the Flutter/Dart mobile app, Python/Django REST backend, PostgreSQL schema, Python AI service, and supporting infrastructure remain unimplemented.

The prototype will not send real emergency alerts, dispatch ambulances, or integrate with emergency organizations. Detection is not confirmation; candidates require authorized human verification. Evidence remains private and backend-authorized, and location claims retain source and uncertainty provenance. Map, object storage, deployment, model, and other provider choices remain pending.

See the [system requirements specification](../requirements/system_requirements_specification.md), [system architecture](../architecture/system_architecture.md), and [open architecture decisions](../architecture/open_architecture_decisions.md).
