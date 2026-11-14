# Data Flow

**Status:** Proposed conceptual flow; not an API or database contract.

## Candidate-to-Incident Flow

~~~mermaid
sequenceDiagram
    actor Owner as Video source owner
    participant AI as AI detection service
    participant API as Django REST backend
    participant DB as PostgreSQL
    participant Store as Object storage
    actor Reviewer as Authorized human reviewer
    participant App as Flutter client
    actor Responder as Police or Hospital user

    Owner->>AI: Supply approved input and source context
    AI->>AI: Validate, preprocess, detect/track, analyze temporal evidence
    alt Processing failure or unauthorized source
        AI-->>Owner: Record failure; do not create verified incident
    else Candidate generated
        AI->>Store: Store evidence under approved restricted policy (future)
        AI->>API: Submit authenticated candidate and evidence reference
        API->>API: Authenticate service; validate provenance and duplicate status
        API->>DB: Record DETECTED candidate and audit event
        API->>DB: Move candidate to UNDER_VERIFICATION
        Reviewer->>App: Review permitted evidence and uncertainty
        App->>API: Submit authorized verification decision
        API->>API: Check reviewer permission and allowed transition
        alt Verified
            API->>DB: Record VERIFIED and decision audit
            API->>DB: Assign to eligible response group (policy TBD)
            API-->>Responder: Create simulated notification/status
            Responder->>App: Acknowledge and update simulated response
            App->>API: Submit authorized response update
            API->>DB: Persist state and audit event
        else Rejected or pending
            API->>DB: Record rejection or retain pending state
        end
    end
~~~

## Data Categories and Ownership

| Data | Source | Authoritative owner | Handling |
|---|---|---|---|
| Raw video | Approved source | Source owner and AI processing boundary | Sensitive; permission, retention, and deletion policy required |
| Detection observations | AI pipeline | AI service until submitted | Preserve timing, provenance, uncertainty, and model/config version when available |
| Candidate and incident state | AI candidate plus authorized decisions | Backend | PostgreSQL; backend validates transitions and audit |
| Evidence media | AI evidence generation | Future object storage under backend policy | Private by default; provider and access mechanism TBD |
| Evidence metadata | AI service and backend | Backend | PostgreSQL reference/provenance metadata; no public media URL |
| User and role data | Admin workflow | Backend | Minimize, protect credentials, audit role changes |
| Response updates | Police/Hospital prototype users | Backend | Simulated; scoped and attributable |
| Notification result | Backend notification component | Backend | Clearly labeled simulated; no emergency dispatch |

## Data-Flow Rules

- A processing failure, missing evidence, or duplicate suspicion is not equivalent to a negative detection or verified incident.
- The backend accepts only an authenticated AI service identity with submission-only capability.
- Backend persistence determines whether an event was accepted; clients do not assume success after a timeout.
- Retry and idempotency details require an agreed future event contract. Duplicate candidates must not silently create duplicate response work.
- Location precision and personal details are minimized; exact policy and retention periods are TBD.
- All media access and state changes are subject to object-level authorization and audit requirements.
