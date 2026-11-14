# Security Baseline

**Status:** Requirements baseline for future implementation.

- Keep secrets out of the repository and use environment-based configuration.
- Authenticate users and enforce role-based access at the backend for every protected operation.
- Validate and constrain incoming data; return safe, consistent errors.
- Use least privilege for accounts, services, and storage.
- Protect credentials and sensitive evidence in transit and at rest according to the selected deployment and storage design.
- Treat incident, location, identity, CCTV, and evidence data as sensitive; minimize collection and define retention and deletion.
- Use synthetic or approved data in development and evaluation.
- Review dependencies and security-sensitive changes; keep logs free of secrets and unnecessary personal data.
- Keep emergency integrations disabled unless explicitly authorized.
- Define backup, incident handling, audit, and access-review practices before deployment.

This baseline is not a claim of implementation or certification. See the repository [security policy](../../SECURITY.md) for reporting and secret handling.
