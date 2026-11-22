# System Requirements Specification

**Status:** REVISED_DRAFT — pending team approval
**Document scope:** Requirements Engineering and System Design

## 1. Purpose

This specification describes the intended behavior, boundaries, users, and acceptance conditions for ResQVision. It is a planning baseline for future implementation, not an approval of operational emergency response or a claim that any service is implemented.

## 2. Project Overview

ResQVision is an academic prototype for analyzing approved road surveillance video, identifying possible accident events, verifying candidates using computer-vision and temporal evidence, managing incident records, and presenting relevant information to authorized Admin, Police, and Hospital users.

The planned system consists of a Flutter mobile client, a Django REST backend, PostgreSQL for structured records, an independent Python AI service, and future object storage for media. Maps and other external providers remain undecided. Any police or hospital response and notification behavior in the prototype is simulated.

## 3. Problem Statement

Accident information may reach response organizations late or without consistent supporting details. This project explores whether a controlled software workflow can organize potential events and supporting evidence for timely human review. Video analysis can produce false positives and false negatives; a model output alone must never be represented as an established real-world accident.

## 4. Objectives

- Analyze authorized video inputs and produce traceable accident candidates.
- Apply temporal verification logic and preserve uncertainty and rejection outcomes.
- Preserve provenance from each AI DetectionEvent through its AccidentCandidate and any resulting AccidentIncident.
- Capture evidence references and metadata under approved privacy and retention rules.
- Create an authoritative AccidentIncident only after an authorized candidate verification decision.
- Track each Police or Hospital ResponseAssignment and Response independently.
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

ResQVision is a new modular system. The backend is the authoritative owner of user identity, permissions, DetectionEvent intake, AccidentCandidate review, AccidentIncident records, assignments, notification records, and audit history. The AI service analyzes inputs and submits observations/evidence; it cannot verify or reject a candidate, create an authoritative incident, or control a response. Police and Hospital assignments have independent statuses and activity histories. The mobile client accesses protected information only through the backend API.

In scope are controlled video processing, candidate generation and verification, evidence metadata, incident lifecycle planning, role-based review, simulated notifications, auditability, and evaluation planning. Real dispatch, live emergency alerts, operational monitoring commitments, and production integrations are out of scope.

## 7. User Classes

| Class | Intended use |
|---|---|
| ADMIN | Manage system users and roles, oversee incidents, and perform proposed review and assignment actions subject to approval |
| POLICE | Review incidents within an authorized assignment or jurisdictional scope and update simulated response status |
| HOSPITAL | Review the minimum information needed for an authorized assignment and update simulated readiness |
| AI service | Submit authenticated DetectionEvents and associated evidence metadata; the backend associates events to candidates; no human login or response authority |
| Maintainer/operator | Configure and support the prototype using least privilege; operational role model remains TBD |

## 8. Operating Environment

The planned client is Flutter/Dart on supported mobile platforms. The planned backend and AI service use Python; Django REST Framework exposes backend capabilities, PostgreSQL stores structured records, and object storage is intended for media. Supported versions, hosting, network topology, device minimums, and deployment provider are TBD. Docker is planned for development but is not configured.

## 9. Conceptual Business Records

These are logical concepts only, not an approved physical schema:

| Concept | Responsibility and relationship |
|---|---|
| VideoSource | Registered input source with owner, authorization, type, location reference, availability/health information, timestamp provenance, input-configuration reference, and processing/retention policy |
| DetectionEvent | One AI-submitted observation with source/model provenance and submission outcome; multiple events may contribute to one AccidentCandidate |
| AccidentCandidate | Potential accident requiring authorized review; has its own RECEIVED, UNDER_REVIEW, VERIFIED, or REJECTED lifecycle |
| AccidentIncident | Authoritative record created by the backend only after candidate verification; has a separate OPEN, RESPONSE_ACTIVE, RESOLVED, or CLOSED lifecycle |
| EvidenceAsset | Media object and metadata linked to a candidate and, where appropriate, referenced by its resulting incident; access policy belongs to the backend |
| ResponseAssignment | One assignment from a verified incident to one eligible Police or Hospital response target; each assignment has an independent lifecycle |
| Response | Activities/status updates for one assignment; Police and Hospital activities are kept separate |
| IncidentStatusHistory / AssignmentStatusHistory | Append-oriented history for incident and assignment transitions |
| Notification | Delivery/read simulation state; never an acknowledgement or source of incident truth |
| AuditEvent | Attributable record of security-sensitive actions and state changes |
| LocationProvenance | Origin, source/timestamp, uncertainty, verification status, and correction history for a location claim |

EvidenceAsset is the canonical name for the controlled media/evidence concept (also called AccidentEvidence in an early concept list).

## 10. Functional Overview

1. A source owner/operator registers or supplies a VideoSource under a documented authorization and data-use policy. Controlled uploaded video remains supported for academic demonstrations.
2. The AI service processes authorized input and submits one or more authenticated DetectionEvents with provenance and evidence metadata.
3. The backend validates machine identity and event integrity, handles repeated event IDs idempotently, and creates or associates AccidentCandidates. Similar but non-identical events are grouped only under an approved policy; uncertain duplicates are flagged for review.
4. An authorized human reviewer moves a candidate from UNDER_REVIEW to VERIFIED or REJECTED. The AI service cannot make this decision.
5. In one backend-consistent operation, a VERIFIED candidate creates and links an authoritative AccidentIncident in OPEN state. A rejected candidate remains distinct and auditable under the approved retention policy.
6. The backend creates separately tracked ResponseAssignments for eligible Police and Hospital targets. Each acknowledgement, response update, completion, inability, cancellation, or approved expiration belongs to its own assignment.
7. Incident state is aggregated separately: OPEN, RESPONSE_ACTIVE, RESOLVED, CLOSED. Notification records have their own delivery state and never imply assignment acknowledgement.
8. Evidence upload is backend-authorized and object-scoped; evidence is validated before becoming AVAILABLE. Evidence retrieval requires backend object-level authorization.
9. Location claims retain provenance and uncertainty. Camera coordinates are not silently treated as the exact accident location.
10. All response, notification, evidence access, and external integrations remain simulated/non-operational for the academic prototype.

## 11. External Interfaces

| Interface | Responsibility and boundary |
|---|---|
| Mobile client to backend | Future authenticated API for role-authorized reads and actions; endpoint names and schemas are not defined here |
| AI service to backend | Future machine-authenticated DetectionEvent and evidence metadata submission; event identity, retry, idempotency, and upload authorization contract must be agreed before implementation |
| Backend to PostgreSQL | Backend-owned structured records and transaction boundaries; no direct database access from mobile or AI client |
| Backend to object storage | Future backend-authorized, short-lived, object-scoped upload/retrieval; direct authorized upload is preferred where supported, with backend-mediated fallback; provider TBD |
| Notification provider | Firebase Cloud Messaging is planned, but live delivery is not configured; prototype notifications remain simulated |
| Maps provider | Provider and permitted location disclosure are TBD |
| Video source | Registered authorized source or controlled uploaded file; streaming mechanism, registration authority, health monitoring, and owner policy are TBD |
| Location source | Camera coordinates, approved GPS metadata, manual verification, or another documented source; provenance and uncertainty must accompany claims |

## 12. Constraints

- This is an academic prototype; no real emergency alerts, dispatch, ambulance deployment, or emergency organization integration.
- DetectionEvent, AccidentCandidate, AccidentIncident, ResponseAssignment, Response, EvidenceAsset, and Notification are distinct concepts.
- AI detection is not confirmation. Only an authorized human verification decision may cause the backend to create an AccidentIncident.
- Police and Hospital assignments and responses are independent. One acknowledgement does not acknowledge the incident or another agency's assignment.
- Use only synthetic or explicitly approved test and evaluation data.
- Do not store private CCTV footage, credentials, or large private datasets in the public repository.
- PostgreSQL is for structured records and metadata; actual media belongs in separately governed object storage.
- Do not select providers, model versions, thresholds, or operational targets without team agreement.
- This scope does not implement services, endpoints, migrations, or production configuration.

## 13. Assumptions and Dependencies

- Admin, Police, and Hospital are the agreed prototype role names.
- The backend will remain the single source of truth for incidents and authorization.
- Video processing and responder-facing workflows will use controlled data and simulated outcomes.
- Implementation depends on agreement about source permissions, human verification authority, incident visibility, retention, evaluation data, and external providers.
- Team ownership, target platforms, deployment environment, and operational support are TBD.

## 14. Acceptance Criteria

The requirements and system design are acceptable for review when:

1. Every functional requirement has a stable identifier, actor, preconditions, flows, postconditions, priority, and testable acceptance criteria.
2. Non-functional requirements separate required controls from unapproved performance and availability targets, which remain TBD.
3. Each functional requirement maps to components, workflows, and planned test coverage.
4. DetectionEvent, AccidentCandidate, and AccidentIncident remain distinct and preserve provenance; an incident is created only after authorized verification.
5. Police/Hospital assignment lifecycles are independent from each other and from incident and notification lifecycles.
6. Evidence upload/retrieval, VideoSource authorization, and LocationProvenance are described without finalizing provider contracts or physical schema.
7. Role permissions and transitions are consistent and marked proposed where approval is still needed.
8. Failure scenarios preserve data consistency, audit events, safe user outcomes, recovery guidance, and approval status.
9. Documentation links and requirement identifiers are validated and no implementation artifacts are introduced.

## 15. Related Documents

See [functional requirements](functional_requirements.md), [non-functional requirements](non_functional_requirements.md), [scope and constraints](scope_and_constraints.md), [use cases](use_cases.md), [role-permission matrix](role_permission_matrix.md), and [requirements traceability](requirements_traceability.md).
