# Trust Boundaries

**Status:** Proposed security design baseline for team review; no security audit or implementation is claimed.

## Boundary Diagram

~~~mermaid
flowchart LR
    subgraph External[External and user-controlled boundary]
        Source[Video source owner]
        Client[Mobile client and user]
        Providers[Optional map / notification providers]
    end
    subgraph Service[Application service boundary]
        AI[AI service]
        API[Backend authorization and business logic]
    end
    subgraph Data[Protected data boundary]
        DB[(PostgreSQL)]
        Store[(Private evidence storage)]
        Logs[(Audit and operational records)]
    end
    Source -->|approved video; validate| AI
    Client -->|credentials and requests; authenticate/authorize| API
    AI -->|candidate only; service identity| API
    API -->|least-privilege access| DB
    API -->|restricted media path| Store
    API -->|minimal data; simulated prototype only| Providers
    API -->|attributable events; redact secrets| Logs
~~~

## Boundaries and Controls

| Boundary | Data crossing it | Main risks | Required design controls |
|---|---|---|---|
| Video source owner to AI service | Video, source identity, time/location metadata, processing permission | Unauthorized footage, malicious media, excessive collection, resource exhaustion | Verify approved source/purpose; validate media; constrain processing; record provenance; define deletion and retention |
| AI service to backend | Candidate event, confidence/uncertainty, evidence references | Spoofed service, replay, duplicate event, forged status, oversized payload | Authenticate service identity; validate and version future contract; restrict capability to submission; apply idempotency/replay controls once agreed |
| Mobile client to backend | Credentials/tokens, incident queries, user actions, location/evidence views | Credential theft, object-level data exposure, privilege escalation, injection | Protected transport; server-side authentication and authorization on every request; input validation; safe errors; rate-limit policy TBD |
| Backend to PostgreSQL | Identity, incident, response, metadata, audit | SQL injection, excessive database privilege, inconsistent transitions, audit tampering | Parameterized access through backend; least-privilege database account; transactional state changes; protect audit records |
| Backend to object storage | Media write/read requests and object references | Public exposure, guessed URLs, cross-tenant access, excessive retention | Private-by-default storage; backend authorization; restricted/short-lived retrieval; encryption and lifecycle policy TBD |
| Backend to notification/map providers | Minimal notification or location data | Data disclosure, provider outage, misdelivery, unintended live alert | Provider review; minimize payload; simulated-only prototype behavior; fail closed from any emergency dispatch path |
| Operator/admin boundary | Secrets, user administration, audit data, deployment controls | Insider misuse, credential leakage, unauthorized configuration | Least privilege, secret management, auditable administration, access review and recovery procedures TBD |

## Sensitive Data

Treat video and evidence media, precise location, incident details, user identity, credentials/tokens, role assignments, and audit trails as sensitive. Use synthetic or explicitly approved data for development and demonstration. Do not put private CCTV or real credentials in the public repository.

## Identity and Authorization

- Human users authenticate through the backend; planned JWT lifecycle details remain TBD.
- The backend authorizes both role and object scope. User interface visibility is not a security boundary.
- The AI service uses a separate machine identity with narrowly limited candidate-submission capability.
- Object storage must not grant clients unrestricted bucket or permanent public access.
- Error responses should avoid confirming sensitive object existence to unauthorized callers.

## Threat and Mitigation Notes

- **False or replayed candidate:** authenticate service requests, preserve provenance, deduplicate where possible, and require authorized verification.
- **Unauthorized incident/evidence access:** enforce object-level checks at every backend operation and test role/scope boundaries.
- **Malicious or corrupt video:** validate formats and resource limits, isolate processing failures, and avoid treating processing errors as negative detections.
- **Credential or token exposure:** never log secrets, protect transport, review token lifecycle, and rotate service credentials under an approved policy.
- **Evidence link leakage:** use constrained retrieval and avoid embedding unrestricted storage URLs in notifications or logs.
- **Unsafe notification behavior:** keep prototype delivery simulated and prohibit fallback to actual emergency channels.
- **Insider or audit abuse:** restrict administrative/audit functions and protect attributable records from ordinary user modification.

## Open Security Decisions

Resolve token expiry/refresh/revocation, service authentication mechanism, storage access and encryption, key rotation, rate limits, audit retention, backup protection, privacy/retention policy, incident response, and privileged access review before deployment.
