# Project Overview

**Status:** REVISED_DRAFT — pending team approval.

ResQVision (AI-Based Road Accident Detection and Emergency Response System) is an academic major project for a team of four. It explores a modular system that analyzes authorized CCTV/video sources, submits AI DetectionEvents, associates them with AccidentCandidates, and creates authoritative AccidentIncidents only after authorized human verification. Role-based users review incidents and manage independent Police and Hospital ResponseAssignments with simulated responses.

The PostgreSQL-backed Django models, migrations, internal domain services, and human-authenticated API are implemented. The Flutter client supports account sign-in and session handling; candidate review and incident-response workflows remain gated. The revised requirements and system-design specification remains pending team approval. The Python AI service, object-storage integration, and deployment infrastructure are not configured.

The prototype will not send real emergency alerts, dispatch ambulances, or integrate with emergency organizations. Detection is not confirmation; candidates require authorized human verification. Evidence remains private and backend-authorized, and location claims retain source and uncertainty provenance. Map, object storage, deployment, model, and other provider choices remain pending.

See the [system requirements specification](../requirements/system_requirements_specification.md), [system architecture](../architecture/system_architecture.md), and [open architecture decisions](../architecture/open_architecture_decisions.md).
