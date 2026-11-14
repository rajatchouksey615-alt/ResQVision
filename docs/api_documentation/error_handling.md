# API Error Response Conventions

**Status:** REVISED_DRAFT — pending team approval; no endpoint implements it yet.

Errors should have a stable machine-readable code, a safe human-readable detail, and optional field-level validation errors. Use the appropriate HTTP status. Do not return stack traces, credentials, internal implementation details, storage paths, or confirmation that an out-of-scope candidate, incident, assignment, or evidence object exists.

Future event-intake outcomes should distinguish accepted, idempotent duplicate, validation rejection, unauthorized service/source, and retryable/unavailable outcomes without defining a wire schema here. Evidence upload and retrieval failures must not mark media AVAILABLE or mutate candidate, incident, assignment, or notification state. A timeout after submission is an unknown outcome and must be safely retried with the same event identity.

Audit security-sensitive denials and state transitions without logging passwords, tokens, camera credentials, or raw media. Keep simulated notification failures clearly separate from assignment acknowledgement and incident state.

Illustrative shape, not an implemented contract:

    {"code":"validation_error","detail":"Request data is invalid.","errors":{"field":["Reason"]}}

Finalize schema and localization needs when API contracts are designed.
