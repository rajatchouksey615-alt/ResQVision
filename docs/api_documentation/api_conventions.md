# REST API Conventions

**Status:** REVISED_DRAFT — pending team approval; endpoint contracts are not implemented.

- Use nouns for resource paths and plural resource names where appropriate.
- Use HTTP methods according to their intended semantics and return suitable status codes.
- Validate all input at the boundary; use consistent machine-readable errors.
- Require authentication and enforce authorization for protected operations.
- Separate human-user JWT authentication from the AI_SERVICE machine identity. Machine permissions must be narrowly scoped; AI_SERVICE cannot verify candidates, create incidents, assign targets, or update response state.
- Enforce object-level authorization for candidate, incident, ResponseAssignment, EvidenceAsset, and LocationProvenance operations. A role alone does not grant access to all objects.
- Use stable DetectionEvent identity and idempotent retry semantics for event intake; candidate grouping/deduplication is separate from event identity.
- Authorize evidence transfer through a backend-issued, short-lived, single-object, operation-scoped mechanism where supported; backend-mediated upload is a fallback. Never issue broad storage credentials or accept arbitrary user object paths.
- Treat evidence availability, incident state, assignment state, and notification delivery state as separate domains.
- Use pagination for potentially large collections and document filtering and ordering.
- Use ISO 8601 timestamps with explicit time-zone handling.
- Avoid returning secrets, internal stack traces, or unnecessary sensitive data.
- Document idempotency and retry behavior for operations that may be repeated.
- Audit candidate decisions, incident creation, each independent assignment/response transition, evidence upload/retrieval/deletion, location correction, and administrative overrides. Do not include secrets or raw media.
- Return safe authorization failures that do not reveal whether out-of-scope evidence or incidents exist.
- Version public API paths deliberately; see api_versioning.md.

Endpoint names, event schemas, upload/completion/retrieval contracts, idempotency keys, object-level policies, and error schemas must be agreed with affected module owners before implementation. These conventions describe capabilities only and do not define an endpoint or wire shape.
