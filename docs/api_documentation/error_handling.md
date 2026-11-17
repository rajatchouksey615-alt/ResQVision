# API Error Handling

All DRF errors use this envelope:

```json
{
  "code": "validation_error",
  "detail": "Request data is invalid.",
  "errors": {"field": ["A value is required."]},
  "request_id": "5a099c5d-2fed-44f4-90cc-07be655f9aa2"
}
```

`errors` is omitted except for field-level validation failures. The request ID is a UUID returned in both the body and `X-Request-ID` response header. A valid client UUID may be reused as the correlation ID; invalid values are replaced.

| Condition | Status | Code |
|---|---:|---|
| Missing or invalid human credentials | 401 | `authentication_failed` |
| Authenticated but denied | 403 | `authorization_denied` |
| Missing or out-of-scope resource | 404 | `not_found` |
| Invalid domain state / conflicting command | 409 | `invalid_state`, `idempotency_conflict`, or `resource_conflict` |
| Request validation failure | 400 | `validation_error` |
| Unapproved policy or disabled machine authentication | 503 | `policy_unavailable` or `machine_authentication_unavailable` |
| Missing evidence storage provider | 503 | `evidence_storage_unavailable` |
| Rate limit exceeded | 429 | `rate_limited` |
| Request body over 1 MiB | 413 | `request_too_large` |

The API does not return tracebacks, SQL errors, credentials, tokens, storage paths, or internal exception details. Queries with defined object scope filter before retrieval; intentionally blocked operations return the same unavailable outcome regardless of supplied resource ID.

Domain writes preserve service-level audit events and idempotency. Passwords, refresh/access tokens, camera credentials, and raw media are not added to audit context.
