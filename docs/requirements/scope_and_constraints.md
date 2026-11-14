# Scope and Constraints

**Status:** Draft for team review. The project is in Phase 1 — Requirements Engineering and System Design; service implementation has not begun.

## Project Scope

ResQVision is an academic prototype for controlled video analysis, accident candidate generation and verification, evidence metadata, incident management, role-based review, and simulated response coordination.

## Phase 1 Design Scope

- Specify responsibilities and boundaries for the planned Flutter client, Django REST backend, PostgreSQL, independent Python AI service, notification component, and future object storage.
- Define requirements for ADMIN, POLICE, and HOSPITAL users, including least-privilege access and proposed incident workflows.
- Describe candidate detection, temporal verification, uncertainty, evidence references, duplicate handling, and incident lifecycle at a conceptual level.
- Identify logical data ownership and relationships only; detailed field definitions and schema remain future work.
- Document security, privacy, failure handling, evaluation expectations, assumptions, and open decisions.

## Planned Prototype Scope

- Process only approved or synthetic video inputs.
- Generate candidates and supporting evidence without claiming unmeasured accuracy or real-time performance.
- Store structured incident state in the backend and use object storage for media when a provider and policy are approved.
- Provide authorized role-based review and simulated police/hospital response tracking.
- Use simulated notification outcomes only.

## Out of Scope

- Real emergency alerts, emergency-service integrations, dispatch, ambulance deployment, or operational response.
- Public or production service operation, service-level commitments, or claims of emergency readiness.
- A final database schema, SQL, Django models, or migrations in this phase.
- Implemented endpoints, serializers, or request/response contracts.
- Unapproved map, object storage, deployment, notification, or AI model provider/version selection.
- Committing private CCTV footage, personal data, secrets, large datasets, uploaded media, or model weights.

## Constraints

- Backend owns identity, authorization, incidents, response state, and audit history.
- The AI service is independent and may submit candidate evidence, but cannot dispatch responders or independently claim an authoritative human verification.
- Structured metadata belongs in PostgreSQL; media belongs in separately governed object storage.
- Data use, location precision, evidence access, and retention require an approved policy.
- Use only controlled synthetic or explicitly approved data for development and demonstration.
- No dependencies are installed and no application services are implemented as part of the requirements/design phase.

## Open Decisions

Maintain the decision register in [open architecture decisions](../architecture/open_architecture_decisions.md). Key items include the verification authority and criteria, source ingestion, data retention, evaluation set and measures, object storage, maps, notification strategy, service communication, deployment, and operational ownership.
