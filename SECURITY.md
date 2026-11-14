# Security Policy

ResQVision is an academic prototype and is not an operational emergency-response service.

## Reporting a Vulnerability

Do not publish exploit details, private incident evidence, credentials, or sensitive video in a public issue. Report suspected vulnerabilities privately to the project maintainers through the repository’s private reporting channel when available, or through a communication channel agreed with the project supervisor. Include affected component, impact, and safe reproduction steps. The project team should acknowledge the report and coordinate remediation before public disclosure.

## Security Requirements

- Do not commit secrets, credentials, private keys, or populated local environment files.
- Use [.env.example](.env.example) only for variable names and non-sensitive placeholders.
- Revoke or rotate credentials if they are exposed; deleting a committed secret does not remove it from Git history.
- Apply authentication, role-based authorization, input validation, and least privilege when services are implemented.
- Treat incident records, location data, evidence, and CCTV footage as sensitive.
- Do not commit private recordings, real personal data, or production data.
- Keep real emergency integrations disabled unless explicitly authorized.
- Review dependencies and security-sensitive changes before adoption.

## Supported Scope

During development, report security issues affecting this repository or the planned prototype to the project team. No production deployment or service-level response commitment is currently defined.
