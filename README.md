# ResQVision

**AI-Based Road Accident Detection and Emergency Response System**

## Project Description

ResQVision is an academic major project exploring how computer vision and coordinated software workflows could help identify potential road accidents from authorized CCTV or video sources. The planned system produces AI DetectionEvents, associates them with AccidentCandidates, creates authoritative AccidentIncidents only after human verification, and presents independently tracked Police and Hospital assignments to authorized users.

The project is in **Phase 4: Authentication, Authorization and REST API Layer**. Phase 1 requirements and architecture documents remain a **REVISED_DRAFT pending team approval**. The PostgreSQL-backed Django foundation, domain services, and a versioned human-authenticated API are implemented. Mobile and AI services, approved machine authentication, object storage, and deployment integrations are not configured.

## Problem Statement

Accident information may reach response organizations late or without consistent supporting details. ResQVision will explore a prototype workflow for identifying potential incidents from video and organizing information for authorized users. Detection results are candidates and must pass verification logic; an AI output alone must not be represented as a confirmed accident.

## Project Objectives

- Establish a modular foundation for a four-member development team.
- Plan a video analysis pipeline for accident candidate detection and temporal verification.
- Define a backend boundary for authentication, authorization, incident records, evidence metadata, and notifications.
- Plan role-based mobile interfaces for Admin, Police, and Hospital users.
- Document security, privacy, testing, and deployment expectations before implementation.

## Core Features

The user-facing applications and external integrations remain planned. Backend domain services now implement core persistence workflows, including event ingestion, candidate review, incident and response transitions, evidence metadata, location claims, and simulated notifications.

- Video and CCTV input processing for vehicle detection and tracking.
- Accident candidate identification followed by verification logic.
- Evidence capture with backend-authorized media access and evidence metadata.
- Separate detection events, accident candidates, and verified incident records.
- Independent Police and Hospital assignments and response tracking, separate from incident-level status.
- Simulated or otherwise non-operational notification flows for the academic prototype.

## System Architecture

The planned system has four main parts:

- **Mobile app:** Flutter and Dart interfaces for Admin, Police, and Hospital users. It will communicate with the backend API and will not access the database directly.
- **Backend:** Python, Django, Django REST Framework, and PostgreSQL. Database/domain services and the `/api/v1/` transport layer are implemented. Human JWT is configured; operations with unresolved authority remain unavailable. AI machine authentication, external notification delivery, and storage integrations remain unconfigured.
- **AI service:** Python, YOLO, OpenCV, PyTorch, and NumPy for authorized video processing, object detection/tracking, DetectionEvent generation, temporal analysis, and evidence generation. It cannot verify candidates or create incidents.
- **Infrastructure and documentation:** A local PostgreSQL Compose definition and database implementation notes are present. No container or production deployment is running. Technical decisions and workflows are documented under docs.

The intended flow is authorized VideoSource input to AI DetectionEvents, backend candidate association, human verification, and authoritative incident creation. Evidence, incident, each agency assignment, and notification delivery have separate backend-owned lifecycles. Integration contracts and physical implementation details remain to be designed.

## Technology Stack

| Area | Planned technology or status |
|---|---|
| Mobile | Flutter, Dart |
| Backend | Python, Django, Django REST Framework |
| Structured data | PostgreSQL |
| Computer vision | YOLO, OpenCV, PyTorch, NumPy |
| Application/service authentication | Human JWT implemented; AI_SERVICE remains separate and disabled pending OAD-017 |
| Push notifications | Firebase Cloud Messaging planned; credentials and live delivery are not configured |
| Maps | Provider pending selection |
| Media storage | Object storage planned; provider pending selection |
| Development environment | Optional local PostgreSQL Compose service; no production services are configured |

## User Roles

- **ADMIN:** planned system and user administration and incident oversight.
- **POLICE:** planned authorized incident review and response status updates.
- **HOSPITAL:** planned authorized incident review and response readiness updates.

Role permissions and workflows are in revised draft and pending team approval. Police and Hospital assignments are independent; these roles do not imply a connection to real emergency services.

## Repository Structure

- mobile_app: Flutter application foundation for Android and Windows, with architecture notes, assets, and unit/widget tests.
- backend: Django configuration, domain models, migrations, internal domain services, versioned REST API, and PostgreSQL-backed tests.
- ai_service: video analysis service foundation, source boundaries, model and dataset policies, and test placeholders.
- infrastructure: future development and deployment configuration conventions.
- docs: requirements, architecture, workflows, database, API, testing, security, deployment, decisions, and academic project documentation.
- scripts: future repository setup and validation scripts.

## Development Roadmap

The project is phase-based and feature-driven, with test-driven development applied as executable features are added. Phase 0 established repository structure and standards; Phase 1 documents requirements and system design; Phase 2B established the database; Phase 3 provides internal domain services; Phase 4 adds authentication, scoped API reads, and approved response commands. Next work is to restore the configured PostgreSQL test connection, resolve outstanding authority decisions, and continue client and AI integrations in their later phases.

## Local Development Overview

See [docs/deployment/local_development.md](docs/deployment/local_development.md) for the local database foundation setup. Use local-only credentials from a private `.env`; do not commit it. The Compose database service is available for a running Docker Engine, and the backend can also use a dedicated local PostgreSQL cluster on port 5433. Provider-specific services remain unconfigured.

## Security Principles

- Keep secrets and local environment files out of version control; use .env.example for safe variable names and placeholders.
- Validate inputs and enforce authentication and role-based authorization at service boundaries.
- Treat incident evidence and location information as sensitive data.
- Restrict CCTV recordings, datasets, model weights, and uploaded media from routine Git commits.
- Use least privilege and document security-sensitive decisions.
- Keep real emergency integrations disabled unless explicitly authorized through the appropriate project process.

## Prototype Limitations

ResQVision is an academic prototype. It must not send real emergency alerts to police stations or hospitals, dispatch ambulances, or trigger real-world response. External emergency integrations remain disabled until explicitly authorized. AI detections are unconfirmed candidates and require verification logic and appropriate human review. No production service, provider, or operational readiness is claimed.

## Testing Strategy

Use test-driven development for feature work. The backend includes 67 Phase 3 persistence/domain tests and 20 Phase 4 API security/integration cases. All 87 PostgreSQL-backed tests passed in the latest run. Mobile, AI, storage-adapter, and end-to-end integration tests remain future work.

## Team Information

ResQVision is an academic major project for a team of four. Team member names and module ownership have not been supplied here; see docs/project_documentation/team_responsibilities.md for an assignment template.

## Project Status

- Current phase: **Phase 4 — Authentication, Authorization and REST API Layer**
- Phase 1 specifications: **REVISED_DRAFT, pending team approval**
- Database: local Django models and migrations applied to a dedicated PostgreSQL development database; no production database or service is configured.
- Internal domain services: implemented with explicit fail-closed policy hooks for authority decisions that remain unresolved.
- Human JWT and `/api/v1/` REST endpoints: implemented; see [API documentation](docs/api_documentation/README.md) for scoped and blocked operations.
- AI machine authentication: disabled pending OAD-017. Mobile app and AI processing service: not implemented.
- Emergency service integrations: disabled and out of scope without explicit authorization.
- Map and object storage providers: pending selection.
- License: pending team and institutional decision; see LICENSE_DECISION.md.

## Documentation

Start with the [documentation index](docs/README.md), [architecture decision records](docs/decisions/README.md), and [contribution guide](CONTRIBUTING.md). See [SECURITY.md](SECURITY.md) for security reporting and [LICENSE_DECISION.md](LICENSE_DECISION.md) for the pending license decision.
