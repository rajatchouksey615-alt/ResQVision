# Project Objectives and Scope

## Objectives

- Maintain a modular foundation for a four-member team.
- Specify a system architecture for approved video analysis, candidate verification, incident management, and role-based access.
- Define evidence metadata, incident transitions, simulated response workflows, security boundaries, and traceable acceptance criteria.
- Plan AI evaluation on approved data with documented uncertainty and limitations.
- Record unresolved product and technical decisions for team review before implementation.

## Phase 1 Scope

Phase 1 produces requirements and high-level system design. It covers the planned Flutter client, Django REST backend, PostgreSQL ownership, independent AI service, evidence-storage boundary, notification simulation, user roles, and end-to-end workflows. It does not implement services, database schema, migrations, API endpoints/contracts, or production configuration.

## Planned Prototype Scope

The future prototype may process approved video, generate and verify accident candidates, manage backend-owned incident records, and present simulated coordination workflows to authorized users.

## Out of Scope

Real emergency dispatch, ambulance deployment, live operational alerts, and automatic confirmation of accidents are out of scope. Provider selection, deployment, operational readiness, and real-world integration require separate review and authorization.

## Current Implementation Status

The repository has completed its foundation setup and is now in the requirements/design phase. Mobile, backend, AI, database, and infrastructure services remain unimplemented.
