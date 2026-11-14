# REST API Conventions

**Status:** Proposed conventions for future APIs; endpoint contracts are not implemented.

- Use nouns for resource paths and plural resource names where appropriate.
- Use HTTP methods according to their intended semantics and return suitable status codes.
- Validate all input at the boundary; use consistent machine-readable errors.
- Require authentication and enforce authorization for protected operations.
- Use pagination for potentially large collections and document filtering and ordering.
- Use ISO 8601 timestamps with explicit time-zone handling.
- Avoid returning secrets, internal stack traces, or unnecessary sensitive data.
- Document idempotency and retry behavior for operations that may be repeated.
- Version public API paths deliberately; see api_versioning.md.

Endpoint names and schemas must be agreed with affected module owners before implementation.
