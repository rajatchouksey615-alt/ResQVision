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

Record accepted significant choices as [architecture decision records](../decisions/README.md) using the ADR template. A planned choice is not an implementation claim.
