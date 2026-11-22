# Security Baseline

**Status:** REVISED_DRAFT — pending team approval. Local JWT/API controls and fail-closed authorization adapters are implemented; this document is not a deployment or security audit.

## Identity and Access

- Human API authentication uses database-backed JWTs and current database state. Protected incident/assignment reads are organization scoped; assignment response commands recheck membership in the domain service.
- The AI_SERVICE identity remains separate from human accounts. Its DRF authenticator interface is present but unconfigured under OAD-017; detection submission returns unavailable until an approved mechanism exists.
- Use framework-supported password hashing; never log or store plaintext passwords.
- Human JWT expiry, refresh rotation, blacklist logout, and password-change revocation are implemented locally. The client must keep tokens in secure platform storage.
- Define privileged account administration, access review, and recovery procedures before deployment.

## Data and Service Protection

- Keep secrets out of the repository and use protected environment or secret-management facilities.
- Protect client/service transport in shared environments and define service authentication and key rotation.
- Bind accepted DetectionEvents to an authorized VideoSource, owner/purpose policy, source timestamp, and provenance; keep camera credentials out of documentation and Git.
- Protect against replay and duplicate-event flooding using an agreed stable event identity, idempotent retries, and rate-limit policy where appropriate.
- Validate and constrain video, event, and API inputs at trust boundaries; apply resource limits to media processing.
- Use safe, consistent errors that do not reveal credentials, stack traces, or out-of-scope incident/evidence existence.
- Use least privilege for application, database, storage, and provider accounts.
- Keep evidence media private by default. Prefer short-lived, single-object, operation-scoped upload/retrieval authorization where supported; use backend-mediated upload as fallback. Validate object reference, type, size, and integrity before availability, and quarantine where required.
- Protect sensitive credentials, incident, location, CCTV, identity, and evidence data in transit and at rest according to the selected deployment and storage design.

## Privacy, Audit, and Operations

- Minimize collected and displayed data; define purpose, location precision, retention, and deletion.
- Use synthetic or explicitly approved data in development and evaluation.
- Record attributable authentication success/failure, role creation/modification and user activation/deactivation, VideoSource authorization, candidate decisions, incident creation/transitions, independent assignment acknowledgement/reassignment/response, resolution/closure/reopen, evidence upload/retrieval/deletion/retention, location correction, and administrative overrides without logging secrets or raw media.
- Preserve independent incident and assignment histories. Audit actor/service identity, timestamp, target, action, and outcome; do not silently overwrite audit history.
- Record location origin, timestamp, uncertainty, verification, and corrections. Do not treat camera coordinates as exact accident coordinates or fabricate precision.
- Review dependencies and security-sensitive changes.
- Define rate limits, backup/restore, incident handling, audit retention, and access review before deployment.
- Keep emergency integrations disabled; prototype notifications and response outcomes remain simulated.

This baseline is not a claim of implementation, security audit, certification, or operational readiness. Retention and legal obligations require institutional review. See the [trust-boundary design](../architecture/trust_boundaries.md) and repository [security policy](../../SECURITY.md) for additional context.
