# ResQVision

**AI-Based Road Accident Detection and Emergency Response System**

## Project Description

ResQVision is an academic major project exploring how computer vision and coordinated software workflows could help identify potential road accidents from CCTV or video input. The planned system will analyze video, identify accident candidates, apply verification logic, capture relevant evidence, create incident records through a backend, and present those records to authorized Admin, Police, and Hospital users.

This repository is currently in **Phase 1: Requirements Engineering and System Design**. Phase 0 established the repository foundation. Phase 1 is producing reviewable requirements and architecture documentation; the mobile application, backend, AI service, database schema, and infrastructure services have not been implemented.

## Problem Statement

Accident information may reach response organizations late or without consistent supporting details. ResQVision will explore a prototype workflow for identifying potential incidents from video and organizing information for authorized users. Detection results are candidates and must pass verification logic; an AI output alone must not be represented as a confirmed accident.

## Project Objectives

- Establish a modular foundation for a four-member development team.
- Plan a video analysis pipeline for accident candidate detection and temporal verification.
- Define a backend boundary for authentication, authorization, incident records, evidence metadata, and notifications.
- Plan role-based mobile interfaces for Admin, Police, and Hospital users.
- Document security, privacy, testing, and deployment expectations before implementation.

## Core Features

The following capabilities are planned. None is implemented yet.

- Video and CCTV input processing for vehicle detection and tracking.
- Accident candidate identification followed by verification logic.
- Evidence capture and storage of evidence metadata.
- Centralized incident records and role-based access.
- Incident review and response status workflows for authorized users.
- Simulated or otherwise non-operational notification flows for the academic prototype.

## System Architecture

The planned system has four main parts:

- **Mobile app:** Flutter and Dart interfaces for Admin, Police, and Hospital users. It will communicate with the backend API and will not access the database directly.
- **Backend:** Python, Django, Django REST Framework, and PostgreSQL for API access, authentication and authorization, incident business logic, evidence metadata, and notification coordination.
- **AI service:** Python, YOLO, OpenCV, PyTorch, and NumPy for video processing, object detection and tracking, candidate identification, temporal verification, and evidence generation.
- **Infrastructure and documentation:** Docker conventions and supporting deployment plans will be introduced when the project reaches the relevant phase. Technical decisions and workflows are documented under docs.

The intended flow is video input to AI candidate analysis and verification, then evidence metadata and an incident record through the backend, and finally authorized review in the mobile app. The integration contracts and implementation details remain to be designed.

## Technology Stack

| Area | Planned technology or status |
|---|---|
| Mobile | Flutter, Dart |
| Backend | Python, Django, Django REST Framework |
| Structured data | PostgreSQL |
| Computer vision | YOLO, OpenCV, PyTorch, NumPy |
| Push notifications | Firebase Cloud Messaging planned; credentials and live delivery are not configured |
| Maps | Provider pending selection |
| Media storage | Object storage planned; provider pending selection |
| Development environment | Docker planned; no services are configured yet |

## User Roles

- **ADMIN:** planned system and user administration and incident oversight.
- **POLICE:** planned authorized incident review and response status updates.
- **HOSPITAL:** planned authorized incident review and response readiness updates.

Role permissions and workflows must be specified and reviewed before implementation. These roles do not imply a connection to real emergency services.

## Repository Structure

- mobile_app: Flutter application foundation, architecture notes, assets, and test placeholders.
- backend: Django service foundation, requirements placeholders, configuration and application boundaries, and test placeholders.
- ai_service: video analysis service foundation, source boundaries, model and dataset policies, and test placeholders.
- infrastructure: future development and deployment configuration conventions.
- docs: requirements, architecture, workflows, database, API, testing, security, deployment, decisions, and academic project documentation.
- scripts: future repository setup and validation scripts.

## Development Roadmap

The project is phase-based and feature-driven, with test-driven development applied as executable features are added. Phase 0 established repository structure and standards; Phase 1 documents requirements and system design. Later implementation and evaluation phases will be planned and reviewed by the team. Likely work areas include service foundations, role and incident workflows, AI candidate analysis and verification, integration, evaluation, and deployment preparation. This roadmap does not claim that any service implementation has started.

## Local Development Overview

The current requirements/design phase does not install dependencies or provide runnable services. Review the module READMEs and docs/deployment/local_development.md for the intended setup approach and the decisions still pending. Do not place real credentials in the repository. Provider-specific service setup will be documented only after the team selects providers.

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

Use test-driven development for feature work: define expected behavior, add focused tests, implement the smallest useful change, and run relevant checks before review. Add unit, integration, API, widget, and evaluation tests as appropriate to each module. The repository currently has test directory placeholders only and does not claim an executable test suite.

## Team Information

ResQVision is an academic major project for a team of four. Team member names and module ownership have not been supplied here; see docs/project_documentation/team_responsibilities.md for an assignment template.

## Project Status

- Current phase: **Phase 1 — Requirements Engineering and System Design**
- Repository modules: planned; implementation has not started.
- Emergency service integrations: disabled and out of scope without explicit authorization.
- Map and object storage providers: pending selection.
- License: pending team and institutional decision; see LICENSE_DECISION.md.

## Documentation

Start with the [documentation index](docs/README.md), [architecture decision records](docs/decisions/README.md), and [contribution guide](CONTRIBUTING.md). See [SECURITY.md](SECURITY.md) for security reporting and [LICENSE_DECISION.md](LICENSE_DECISION.md) for the pending license decision.
