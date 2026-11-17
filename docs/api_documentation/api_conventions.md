# REST API Conventions

**Status:** Implemented for the current `/api/v1/` prototype contract. Role and authority documents remain revised drafts; operations depending on unresolved decisions stay unavailable.

- Use plural resource paths and explicit HTTP methods. Lifecycle changes use named `POST` commands; clients cannot patch status fields.
- Validate request data at the DRF boundary. Serializers expose only explicit fields; sensitive models never use `fields = "__all__"`.
- Human API requests use `Authorization: Bearer <access_token>`. The AI_SERVICE endpoint uses a separate authenticator interface and accepts no caller-supplied identity claim.
- Apply authorization before pagination and serialization. Incident and assignment reads are limited to active matching organization memberships. A role or Django superuser flag does not bypass object scope.
- Candidate, source administration, incident resolution/closure, cancellation/reassignment, evidence, and location operations remain unavailable until the relevant policy or provider is approved.
- Domain writes call the existing owning service. Command endpoints accept a UUID `command_id`; a repeated command with the same intent replays safely, while conflicting intent returns `409`.
- Collections use limit/offset pagination, default `25`, maximum `100`. Only documented `status` filters are accepted; arbitrary ORM filters and ordering are not exposed.
- Timestamps use timezone-aware ISO 8601 JSON values. The backend stores and operates in UTC.
- Error bodies use a stable code, safe detail, optional field errors, and request ID. Inaccessible objects are filtered before retrieval where scope is defined.
- Request bodies are limited to 1 MiB. Login and token refresh have dedicated DRF throttles; production deployment must also configure reverse-proxy rate limiting.
- Domain services retain audit behavior for state-changing commands. Passwords and tokens are never placed in audit contexts or URLs.

See the [endpoint reference](endpoint_reference.md) for the exact current wire contract and intentionally unavailable routes.
