# ResQVision API Documentation

The versioned API is mounted at `/api/v1/`. This is an academic prototype and not an operational emergency response system. Human requests use JWT authentication. Machine authentication is a separate boundary and remains disabled while OAD-017 is unresolved.

## Documents

- [Endpoint reference](endpoint_reference.md): implemented routes, scopes, and unavailable operations.
- [Authentication contract](authentication_contract.md): login, token rotation, logout, password change, and throttling.
- [Authorization contract](authorization_contract.md): actor resolution, assignment scope, and fail-closed rules.
- [API conventions](api_conventions.md): request, pagination, filtering, idempotency, and response rules.
- [Error handling](error_handling.md): stable error envelope and status mapping.
- [Versioning policy](api_versioning.md): `/api/v1/` contract policy.
- [OpenAPI schema](openapi.yaml): generated with drf-spectacular 0.30.0.
- [API testing results](api_testing_results.md): commands and latest observed results.

Interactive schema UI is available at `/api/v1/docs/`; the OpenAPI document is served at `/api/v1/schema/`. Do not publish the schema with production server URLs until deployment is approved.
