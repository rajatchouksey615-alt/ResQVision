# Security Baseline

**Status:** Requirements baseline for future implementation; controls have not been verified or deployed.

## Identity and Access

- Authenticate human users at the backend and authorize every protected operation by role and object scope. Client-side visibility is not an authorization control.
- Use a separate, least-privilege machine identity for the AI service. Its planned capability is limited to candidate submission.
- Use framework-supported password hashing; never log or store plaintext passwords.
- Define JWT issuance, expiry, refresh, revocation, logout, storage, and rotation before implementation.
- Define privileged account administration, access review, and recovery procedures before deployment.

## Data and Service Protection

- Keep secrets out of the repository and use protected environment or secret-management facilities.
- Protect client/service transport in shared environments and define service authentication and key rotation.
- Validate and constrain video, event, and API inputs at trust boundaries; apply resource limits to media processing.
- Use safe, consistent errors that do not reveal credentials, stack traces, or out-of-scope incident/evidence existence.
- Use least privilege for application, database, storage, and provider accounts.
- Keep evidence media private by default and return it only through backend-authorized, restricted access.
- Protect sensitive credentials, incident, location, CCTV, identity, and evidence data in transit and at rest according to the selected deployment and storage design.

## Privacy, Audit, and Operations

- Minimize collected and displayed data; define purpose, location precision, retention, and deletion.
- Use synthetic or explicitly approved data in development and evaluation.
- Record attributable role changes, sensitive access, verification, assignment, incident transitions, and administrative actions without logging secrets or unnecessary raw media.
- Review dependencies and security-sensitive changes.
- Define rate limits, backup/restore, incident handling, audit retention, and access review before deployment.
- Keep emergency integrations disabled; prototype notifications and response outcomes remain simulated.

This baseline is not a claim of implementation, security audit, certification, or operational readiness. See the [trust-boundary design](../architecture/trust_boundaries.md) and repository [security policy](../../SECURITY.md) for additional context.
