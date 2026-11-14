# System Requirements Specification

**Status:** Draft for team review
**Project phase:** Phase 1 — Requirements Engineering and System Design

## 1. Purpose

This specification describes the intended behavior, boundaries, users, and acceptance conditions for ResQVision. It is a planning baseline for a later implementation phase, not an approval of operational emergency response or a claim that any service is implemented.

## 2. Project Overview

ResQVision is an academic prototype for analyzing approved road surveillance video, identifying possible accident events, verifying candidates using computer-vision and temporal evidence, managing incident records, and presenting relevant information to authorized Admin, Police, and Hospital users.

The planned system consists of a Flutter mobile client, a Django REST backend, PostgreSQL for structured records, an independent Python AI service, and future object storage for media. Maps and other external providers remain undecided. Any police or hospital response and notification behavior in the prototype is simulated.

## 3. Problem Statement

Accident information may reach response organizations late or without consistent supporting details. This project explores whether a controlled software workflow can organize potential events and supporting evidence for timely human review. Video analysis can produce false positives and false negatives; a model output alone must never be represented as an established real-world accident.

## 4. Objectives

- Analyze authorized video inputs and produce traceable accident candidates.
- Apply temporal verification logic and preserve uncertainty and rejection outcomes.
- Capture evidence references and metadata under approved privacy and retention rules.
- Create a single backend-owned incident record for each accepted event.
- Give authorized roles relevant incident visibility and simulated response tracking.
- Make system behavior, security boundaries, failures, and unresolved decisions reviewable.

## 5. Stakeholders

| Stakeholder | Interest |
|---|---|
| Academic project team | Requirements, architecture, implementation planning, and evaluation |
| Admin users | User and role administration, incident oversight, and proposed review/assignment functions |
| Police users | Authorized incident review and simulated response status updates |
| Hospital users | Authorized incident review and simulated response readiness updates |
| Video/data owners | Permission, purpose limitation, protection, retention, and deletion of source material |
| Future maintainers and operators | Secure, supportable service boundaries and observable failure handling |
| Institutional reviewers | Scope, safety, privacy, and academic evaluation |

## 6. Product Perspective and System Boundaries

ResQVision is a new modular system. The backend is the authoritative owner of user identity, permissions, incident records, response state, and audit history. The AI service analyzes inputs and submits candidate evidence; it is not an authority to contact responders or dispatch services. The mobile client accesses protected information only through the backend API.

In scope are controlled video processing, candidate generation and verification, evidence metadata, incident lifecycle planning, role-based review, simulated notifications, auditability, and evaluation planning. Real dispatch, live emergency alerts, operational monitoring commitments, and production integrations are out of scope.

## 7. User Classes

| Class | Intended use |
|---|---|
| ADMIN | Manage system users and roles, oversee incidents, and perform proposed review and assignment actions subject to approval |
| POLICE | Review incidents within an authorized assignment or jurisdictional scope and update simulated response status |
| HOSPITAL | Review the minimum information needed for an authorized assignment and update simulated readiness |
| AI service | Submit machine-generated candidate evidence through an authenticated service boundary; no human login or response authority |
| Maintainer/operator | Configure and support the prototype using least privilege; operational role model remains TBD |

## 8. Operating Environment

The planned client is Flutter/Dart on supported mobile platforms. The planned backend and AI service use Python; Django REST Framework exposes backend capabilities, PostgreSQL stores structured records, and object storage is intended for media. Supported versions, hosting, network topology, device minimums, and deployment provider are TBD. Docker is planned for development but is not configured.

## 9. Functional Overview

1. An authorized source supplies video under a documented data-use policy.
2. The AI service validates and analyzes the input, tracks relevant objects where useful, and generates a candidate with supporting evidence and uncertainty.
3. A verification workflow evaluates temporal evidence and, under a policy still to be approved, obtains authorized human review before an incident is treated as verified.
4. The backend authenticates the submitting service, deduplicates where possible, records the authoritative incident and audit history, and retains evidence metadata.
5. Authorized users review incidents and update permitted simulated response states through the mobile client.
6. Notifications are recorded or simulated; no real emergency organization is contacted.

## 10. External Interfaces

| Interface | Responsibility and boundary |
|---|---|
| Mobile client to backend | Future authenticated API for role-authorized reads and actions; endpoint names and schemas are not defined here |
| AI service to backend | Future authenticated event submission; event identity, retry, and idempotency contract must be agreed before implementation |
| Backend to PostgreSQL | Backend-owned structured records and transaction boundaries; no direct database access from mobile or AI client |
| Backend to object storage | Future controlled media write/read using short-lived or otherwise restricted access; provider and exact mechanism TBD |
| Notification provider | Firebase Cloud Messaging is planned, but live delivery is not configured; prototype notifications remain simulated |
| Maps provider | Provider and permitted location disclosure are TBD |
| Video source | Approved files or a reviewed source integration; ingestion mechanism and source ownership are TBD |

## 11. Constraints

- This is an academic prototype; no real emergency alerts, dispatch, ambulance deployment, or emergency organization integration.
- AI detection is not confirmation. Verification and suitable human review must be defined.
- Use only synthetic or explicitly approved test and evaluation data.
- Do not store private CCTV footage, credentials, or large private datasets in the public repository.
- PostgreSQL is for structured records and metadata; actual media belongs in separately governed object storage.
- Do not select providers, model versions, thresholds, or operational targets without team agreement.
- This phase does not implement services, endpoints, migrations, or production configuration.

## 12. Assumptions and Dependencies

- Admin, Police, and Hospital are the agreed prototype role names.
- The backend will remain the single source of truth for incidents and authorization.
- Video processing and responder-facing workflows will use controlled data and simulated outcomes.
- Implementation depends on agreement about source permissions, human verification authority, incident visibility, retention, evaluation data, and external providers.
- Team ownership, target platforms, deployment environment, and operational support are TBD.

## 13. Acceptance Criteria

The requirements and design phase is acceptable for review when:

1. Every functional requirement has a stable identifier, actor, preconditions, flows, postconditions, priority, and testable acceptance criteria.
2. Non-functional requirements separate required controls from unapproved performance and availability targets, which remain TBD.
3. Each functional requirement maps to components, workflows, and planned test coverage.
4. Role permissions and incident transitions are consistent and clearly marked as proposed where not approved.
5. Diagrams and workflows preserve the separation between AI candidate evidence and authorized incident verification.
6. All unresolved decisions and assumptions are visible, and no live emergency capability is implied.
7. Documentation links and identifiers are validated and no implementation artifacts are introduced.

## 14. Related Documents

See [functional requirements](functional_requirements.md), [non-functional requirements](non_functional_requirements.md), [scope and constraints](scope_and_constraints.md), [use cases](use_cases.md), [role-permission matrix](role_permission_matrix.md), and [requirements traceability](requirements_traceability.md).
