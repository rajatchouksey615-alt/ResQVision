# Scope and Constraints

**Status:** REVISED_DRAFT — pending team approval. This document covers requirements engineering and system design; service implementation status is described separately.

## Project Scope

ResQVision is an academic prototype for controlled video analysis, accident candidate generation and verification, evidence metadata, incident management, role-based review, and simulated response coordination.

## Requirements and Design Scope

- Specify responsibilities and boundaries for the planned Flutter client, Django REST backend, PostgreSQL, independent Python AI service, notification component, and future object storage.
- Define requirements for ADMIN, POLICE, and HOSPITAL users, including least-privilege access and proposed incident workflows.
- Keep DetectionEvent, AccidentCandidate, AccidentIncident, ResponseAssignment, Response, EvidenceAsset, Notification, and history concepts distinct.
- Describe temporal verification, uncertainty, multi-event candidate association, duplicate handling, and separate candidate, incident, assignment, notification, and evidence lifecycles.
- Define conceptual VideoSource authorization, evidence upload/retrieval, and LocationProvenance without finalizing providers or physical fields.
- Identify logical data ownership and relationships only; detailed field definitions and schema remain future work.
- Document security, privacy, failure handling, evaluation expectations, assumptions, and open decisions.

## Planned Prototype Scope

- Process only approved or synthetic video inputs.
- Generate DetectionEvents and associate them to AccidentCandidates without claiming unmeasured accuracy or real-time performance.
- Create an authoritative AccidentIncident only after authorized candidate verification; retain rejected candidates separately for approved audit/evaluation.
- Store structured records in the backend and use backend-authorized, object-scoped object storage for evidence when a provider and policy are approved.
- Provide authorized role-based review and independently track simulated Police and Hospital assignments and responses.
- Use simulated notification outcomes only.

## Out of Scope

- Real emergency alerts, emergency-service integrations, dispatch, ambulance deployment, or operational response.
- Public or production service operation, service-level commitments, or claims of emergency readiness.
- A final database schema, SQL, Django models, or migrations in this scope.
- Implemented endpoints, serializers, or request/response contracts.
- Unapproved map, object storage, deployment, notification, or AI model provider/version selection.
- Committing private CCTV footage, personal data, secrets, large datasets, uploaded media, or model weights.

## Constraints

- Backend owns identity, authorization, DetectionEvent intake, AccidentCandidate review, AccidentIncident records, assignments, notification records, and audit history.
- The AI service is independent and may submit DetectionEvents and associated evidence metadata; the backend associates events to candidates. AI_SERVICE cannot verify/reject candidates, create incidents, or dispatch responders.
- Backend creates an incident only after a valid human verification decision and preserves provenance from source through event, candidate, evidence, and incident.
- Incident lifecycle, each agency assignment, notification delivery state, and evidence lifecycle remain separate; notification is not acknowledgement.
- Structured metadata belongs in PostgreSQL; media belongs in separately governed object storage.
- Data use, location provenance/precision, evidence access, source registration, and retention require an approved policy.
- Use only controlled synthetic or explicitly approved data for development and demonstration.
- No dependencies are installed and no application services are implemented as part of the requirements/design work.

## Open Decisions

Maintain the decision register in [open architecture decisions](../architecture/open_architecture_decisions.md). Key items include verification authority, assignment aggregation/timeout, source registration and ingestion, location correction, evidence scanning and retention, evaluation data, object storage, maps, notification strategy, service communication, deployment, and operational ownership.
