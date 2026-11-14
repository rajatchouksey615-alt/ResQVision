# Trust Boundaries

**Status:** REVISED_DRAFT — pending team approval; no security audit or implementation is claimed.

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
    AI -->|events and scoped evidence transfer; service identity| API
    API -->|least-privilege access| DB
    API -->|short-lived object-scoped authorization| AI
    AI -->|authorized single-object transfer| Store
    API -->|mediated fallback and retrieval| Store
    API -->|minimal data; simulated prototype only| Providers
    API -->|attributable events; redact secrets| Logs
~~~

## Boundaries and Controls

| Boundary | Data crossing it | Main risks | Required design controls |
|---|---|---|---|
| Video source owner to AI service | Video, source identity, time/location metadata, processing permission | Unauthorized footage, malicious media, excessive collection, resource exhaustion | Verify approved source/purpose; validate media; constrain processing; record provenance; define deletion and retention |
| AI service to backend | DetectionEvents, provenance, scoped EvidenceAsset upload requests/completion | Spoofed/compromised service, replay, duplicate flooding, forged status, oversized payload | Separate AI_SERVICE identity; validate source/event identity; allow only event submission and short-lived scoped upload/report-completion; never grant candidate decision, incident, assignment, response, or general media read |
| Mobile client to backend | Credentials/tokens, incident queries, user actions, location/evidence views | Credential theft, object-level data exposure, privilege escalation, injection | Protected transport; server-side authentication and authorization on every request; input validation; safe errors; rate-limit policy TBD |
| Backend to PostgreSQL | Identity, incident, response, metadata, audit | SQL injection, excessive database privilege, inconsistent transitions, audit tampering | Parameterized access through backend; least-privilege database account; transactional state changes; protect audit records |
| Backend/AI service to object storage | Short-lived single-object upload/read instruction and object reference | Public exposure, guessed/arbitrary keys, credential leakage, cross-object access, oversized/malicious media | Backend authorization; server-controlled unpredictable object identity; operation-scoped expiring transfer; validate object/type/size/integrity; quarantine as required; no broad credentials; lifecycle policy TBD |
| Backend to notification/map providers | Minimal notification or location data | Data disclosure, provider outage, misdelivery, unintended live alert | Provider review; minimize payload; simulated-only prototype behavior; fail closed from any emergency dispatch path |
| Operator/admin boundary | Secrets, user administration, audit data, deployment controls | Insider misuse, credential leakage, unauthorized configuration | Least privilege, secret management, auditable administration, access review and recovery procedures TBD |

## Sensitive Data

Treat video and evidence media, precise location, incident details, user identity, credentials/tokens, role assignments, and audit trails as sensitive. Use synthetic or explicitly approved data for development and demonstration. Do not put private CCTV or real credentials in the public repository.

## Identity and Authorization

- Human users authenticate through the backend; planned JWT lifecycle details remain TBD.
- The backend authorizes both role and object scope. User interface visibility is not a security boundary.
- The AI service uses a separate machine identity limited to DetectionEvent submission and scoped EvidenceAsset upload authorization/completion.
- Object storage must not grant clients unrestricted bucket or permanent public access.
- Error responses should avoid confirming sensitive object existence to unauthorized callers.

## Threat and Mitigation Notes

- **Forged, replayed, or flooded DetectionEvents:** authenticate AI_SERVICE, use stable event identity/idempotent handling, rate-limit consideration, preserve provenance, and keep event-level retries separate from candidate matching.
- **Unauthorized CCTV ingestion:** require VideoSource authorization and owner/purpose reference before processing; suspend/revoke without accepting new events.
- **Unauthorized incident/evidence access:** enforce object-level checks at every backend operation and test role/scope boundaries.
- **Malicious or corrupt video:** validate formats and resource limits, isolate processing failures, and avoid treating processing errors as negative detections.
- **Credential or token exposure:** never log secrets, protect transport, review token lifecycle, and rotate service credentials under an approved policy.
- **Evidence link/object leakage:** use constrained upload/retrieval, server-controlled object IDs, short-lived scoped authorization, validation/quarantine, and avoid unrestricted storage paths in logs/UI.
- **Location disclosure or misattribution:** retain LocationProvenance/uncertainty; distinguish camera coordinates from accident estimates and scope access.
- **Audit log tampering:** append attributable transitions, restrict audit access, and define integrity, retention, backup, and review policy.
- **Unsafe notification behavior:** keep prototype delivery simulated and prohibit fallback to actual emergency channels.
- **Insider or audit abuse:** restrict administrative/audit functions and protect attributable records from ordinary user modification.

## Open Security Decisions

Resolve token expiry/refresh/revocation, AI_SERVICE mechanism/rotation/replay controls, source registry permissions, upload/access authorization support, validation/scanning, storage encryption, rate limits, audit retention/integrity, backup protection, privacy/location/retention policy, incident response, and privileged access review before deployment. Legal obligations and retention periods require institutional review; no compliance certification is claimed.
