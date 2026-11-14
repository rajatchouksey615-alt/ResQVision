# Scope and Constraints

## Project Scope

ResQVision is an academic prototype exploring video-based road accident candidate detection, verification, evidence metadata, incident management, and role-based review workflows.

## In Scope for the Planned System

- A modular Flutter client, Django REST backend, PostgreSQL database, and Python AI service.
- Admin, Police, and Hospital role concepts.
- Video analysis with candidate identification and verification logic.
- Incident records and evidence metadata, with actual media intended for object storage.
- Simulated notification and response workflows suitable for a prototype.

## Constraints and Exclusions

- No real emergency alerts, dispatch, ambulance deployment, or operational response.
- External emergency integrations stay disabled until explicitly authorized.
- AI detections are not automatically confirmed accidents; verification and human review requirements must be defined.
- Map and object storage providers are pending selection. Firebase Cloud Messaging is planned but not configured.
- Do not commit private CCTV, real personal data, large datasets, uploaded media, or large model weights.
- PostgreSQL is planned for structured records and evidence metadata; actual media files will use an object storage provider selected later.
- Phase 0 establishes documentation and repository structure only; no service implementation or dependency installation is in scope.

## Open Questions

Record decisions about user workflows, data retention, dataset permissions, verification thresholds, provider choices, and evaluation criteria in the appropriate requirements documents or ADRs.
