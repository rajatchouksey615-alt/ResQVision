# API Error Response Conventions

**Status:** Proposed response convention; no endpoint implements it yet.

Errors should have a stable machine-readable code, a safe human-readable detail, and optional field-level validation errors. Use the appropriate HTTP status. Do not return stack traces, credentials, or internal implementation details. Keep messages useful without disclosing sensitive incident data.

Illustrative shape, not an implemented contract:

    {"code":"validation_error","detail":"Request data is invalid.","errors":{"field":["Reason"]}}

Finalize schema and localization needs when API contracts are designed.
