# Architecture Documentation

**Documentation status:** REVISED_DRAFT — pending team approval. Internal Django services, selected authenticated REST endpoints, and the Flutter incident read experience are implemented. Production storage, map, live notification, and emergency-service integrations are not enabled; several authority-gated routes remain blocked.

## Index

- [Architecture overview](architecture_overview.md): concise system context, responsibilities, and principles.
- [System architecture](system_architecture.md): goals, containers, communication, ownership, failures, security, and trade-offs.
- [Component architecture](component_architecture.md): responsibility boundaries and cross-component dependencies.
- [Trust boundaries](trust_boundaries.md): sensitive data, threats, and baseline controls.
- [Data flow](data_flow.md): source ingestion, event-to-candidate association, evidence upload/retrieval, location provenance, and independent response data flow.
- [Technology decisions](technology_decisions.md): planned stack and status.
- [Open architecture decisions](open_architecture_decisions.md): unresolved options and trade-offs.
- [Domain governance and decision resolution](domain/governance_overview.md): repository audit, proposed domain policies, authorization matrix, OAD reconciliation, and implementation readiness.
- [Accident verification and emergency response governance workflow](domain/accident_verification_emergency_response_workflow.md): project-owner-approved Police-first verification and simulated Hospital response sequence, with pending policy boundaries, candidate review proposal, and acceptance criteria.
- [Police candidate review architecture blueprint](domain/police_candidate_review_architecture_blueprint.md): owner-approved assignment-scoped Police review policy, current runtime gaps, verification consistency controls, Flutter integration, and candidate-review readiness gates.
- [Candidate review and verification policy](domain/candidate_review_verification_policy.md): approved reviewer scope, assignment-authority boundary, three decision outcomes, audit requirements, and implementation compatibility.
- [Candidate review implementation readiness](domain/implementation_readiness.md): capability-by-capability readiness, unresolved security dependencies, and candidate-review entry decision.
- [Domain governance decision register](decisions/domain_governance_decision_register.md): existing OAD mapping and dated project-owner approval records.

Record accepted significant choices as [architecture decision records](../decisions/README.md) using the ADR template. A planned choice is not an implementation claim.
