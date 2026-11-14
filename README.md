# ResQVision

**AI-Based Road Accident Detection and Emergency Response System**

## Project Description

ResQVision is an academic major project exploring how computer vision and coordinated software workflows could help identify potential road accidents from authorized CCTV or video sources. The planned system produces AI DetectionEvents, associates them with AccidentCandidates, creates authoritative AccidentIncidents only after human verification, and presents independently tracked Police and Hospital assignments to authorized users.

The project is in **Phase 2B: Database Foundation**. Phase 1 requirements and architecture documents remain a **REVISED_DRAFT pending team approval**. A local Django/PostgreSQL data foundation and its schema tests are implemented; API endpoints, mobile and AI services, object storage, and deployment integrations are not.

## Problem Statement

Accident information may reach response organizations late or without consistent supporting details. ResQVision will explore a prototype workflow for identifying potential incidents from video and organizing information for authorized users. Detection results are candidates and must pass verification logic; an AI output alone must not be represented as a confirmed accident.

## Project Objectives

- Establish a modular foundation for a four-member development team.
- Plan a video analysis pipeline for accident candidate detection and temporal verification.
- Define a backend boundary for authentication, authorization, incident records, evidence metadata, and notifications.
- Plan role-based mobile interfaces for Admin, Police, and Hospital users.
- Document security, privacy, testing, and deployment expectations before implementation.

## Core Features

These user-facing capabilities remain planned. The database foundation persists the domain records, but the workflows and integrations below are not implemented.

- Video and CCTV input processing for vehicle detection and tracking.
- Accident candidate identification followed by verification logic.
- Evidence capture with backend-authorized media access and evidence metadata.
- Separate detection events, accident candidates, and verified incident records.
- Independent Police and Hospital assignments and response tracking, separate from incident-level status.
- Simulated or otherwise non-operational notification flows for the academic prototype.

## System Architecture

The planned system has four main parts:

- **Mobile app:** Flutter and Dart interfaces for Admin, Police, and Hospital users. It will communicate with the backend API and will not access the database directly.
- **Backend:** Python, Django, Django REST Framework, and PostgreSQL. The database foundation and custom account model are implemented; APIs, authentication flows, domain services, and notification coordination remain future work.
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
| Application/service authentication | Human JWT planned; separate AI_SERVICE machine identity and scoped permissions required, mechanism TBD |
| Push notifications | Firebase Cloud Messaging planned; credentials and live delivery are not configured |
| Maps | Provider pending selection |
| Media storage | Object storage planned; provider pending selection |
| Development environment | Docker planned; no services are configured yet |

## User Roles

- **ADMIN:** planned system and user administration and incident oversight.
- **POLICE:** planned authorized incident review and response status updates.
- **HOSPITAL:** planned authorized incident review and response readiness updates.

Role permissions and workflows are in revised draft and pending team approval. Police and Hospital assignments are independent; these roles do not imply a connection to real emergency services.

## Repository Structure

- mobile_app: Flutter application foundation, architecture notes, assets, and test placeholders.
- backend: Django configuration, domain models, migrations, and PostgreSQL-backed tests; API implementation remains future work.
- ai_service: video analysis service foundation, source boundaries, model and dataset policies, and test placeholders.
- infrastructure: future development and deployment configuration conventions.
- docs: requirements, architecture, workflows, database, API, testing, security, deployment, decisions, and academic project documentation.
- scripts: future repository setup and validation scripts.

## Development Roadmap

The project is phase-based and feature-driven, with test-driven development applied as executable features are added. Phase 0 established repository structure and standards; Phase 1 documents requirements and system design. Later implementation and evaluation phases will be planned and reviewed by the team. Likely work areas include service foundations, role and incident workflows, AI candidate analysis and verification, integration, evaluation, and deployment preparation. This roadmap does not claim that any service implementation has started.

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

Use test-driven development for feature work. The Django foundation currently has 50 PostgreSQL-backed tests for identity, audit, source, detection, candidate/incident, location, evidence, response, and notification constraints. API, mobile, AI, storage-adapter, and system integration tests remain future work.

## Team Information

ResQVision is an academic major project for a team of four. Team member names and module ownership have not been supplied here; see docs/project_documentation/team_responsibilities.md for an assignment template.

## Project Status

- Current phase: **Phase 2B — Database Foundation**
- Phase 1 specifications: **REVISED_DRAFT, pending team approval**
- Database: local Django models and migrations applied to a dedicated PostgreSQL development database; no production database or service is configured.
- API, mobile app, and AI service: not implemented.
- Emergency service integrations: disabled and out of scope without explicit authorization.
- Map and object storage providers: pending selection.
- License: pending team and institutional decision; see LICENSE_DECISION.md.

## Documentation

Start with the [documentation index](docs/README.md), [architecture decision records](docs/decisions/README.md), and [contribution guide](CONTRIBUTING.md). See [SECURITY.md](SECURITY.md) for security reporting and [LICENSE_DECISION.md](LICENSE_DECISION.md) for the pending license decision.
