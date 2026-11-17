# API Versioning Policy

The initial API uses the explicit `/api/v1/` prefix from its first release. URL routing is centralized in `backend/api/v1/urls.py` and mounted once by `backend/config/urls.py`.

Additive compatible changes may remain in v1. Changes that alter existing field meaning, remove fields, or change authorization behavior require a reviewed new major version and a client migration plan. Do not remove a version until its clients and retirement date have been reviewed.

Phase 1 and role-policy documents remain revised drafts. This API contract does not approve the unresolved authority decisions listed in the [authorization contract](authorization_contract.md).
