# Phase 2 Relational Entity Relationship Design

**Status:** PHASE_2_DESIGN_DRAFT — logical and physical proposal; pending policy/provider review. This document is a design artifact and makes no claim about deployed database objects.

This ERD describes the proposed PostgreSQL tables at implementation-planning level. The separate [schema specification](database_schema_specification.md) and [data dictionary](data_dictionary.md) define ownership, keys, fields and types. This is a design artifact, not executable SQL or a Django model file.

## Mermaid ERD

~~~mermaid
erDiagram
    APP_USER {
        uuid id PK
        varchar email UK
        varchar password
        boolean is_active
        timestamptz date_joined
    }
    AUTH_GROUP {
        bigint id PK
        varchar name UK
    }
    AUTH_PERMISSION {
        bigint id PK
        varchar codename
    }
    ORGANIZATION {
        uuid id PK
        varchar code UK
        varchar organization_kind
        varchar status
    }
    ORGANIZATION_MEMBERSHIP {
        uuid id PK
        uuid user_id FK
        uuid organization_id FK
        bigint role_group_id FK
        boolean is_active
    }
    VIDEO_SOURCE {
        uuid id PK
        varchar source_code UK
        uuid owner_organization_id FK
        varchar authorization_status
        varchar availability_status
    }
    DETECTION_EVENT {
        uuid id PK
        uuid video_source_id FK
        varchar external_event_id
        varchar model_name
        varchar model_version
        timestamptz detected_at
        timestamptz received_at
    }
    ACCIDENT_CANDIDATE {
        uuid id PK
        varchar status
        timestamptz created_at
        timestamptz updated_at
    }
    CANDIDATE_DETECTION_EVENT {
        uuid id PK
        uuid candidate_id FK
        uuid detection_event_id FK
        timestamptz linked_at
    }
    CANDIDATE_REVIEW {
        uuid id PK
        uuid candidate_id FK, UK
        uuid reviewer_id FK
        uuid command_id UK
        varchar decision
        timestamptz reviewed_at
    }
    ACCIDENT_INCIDENT {
        uuid id PK
        uuid candidate_id FK, UK
        varchar status
        timestamptz created_at
    }
    EVIDENCE_ASSET {
        uuid id PK
        uuid source_detection_event_id FK
        varchar storage_provider
        varchar storage_namespace
        varchar object_key
        varchar status
        bigint size_bytes
    }
    EVIDENCE_ASSOCIATION {
        uuid id PK
        uuid evidence_asset_id FK
        uuid video_source_id FK
        uuid candidate_id FK
        uuid incident_id FK
    }
    EVIDENCE_UPLOAD_SESSION {
        uuid id PK
        uuid evidence_asset_id FK
        varchar service_ref
        varchar status
        timestamptz expires_at
    }
    LOCATION_RECORD {
        uuid id PK
        uuid subject_video_source_id FK
        uuid subject_candidate_id FK
        uuid subject_incident_id FK
        uuid source_video_source_id FK
        uuid source_detection_event_id FK
        numeric latitude
        numeric longitude
        varchar claim_kind
        varchar source_method
    }
    LOCATION_CORRECTION_HISTORY {
        uuid id PK
        uuid location_record_id FK
        uuid corrected_by_user_id FK
        timestamptz corrected_at
        text reason
    }
    RESPONSE_ASSIGNMENT {
        uuid id PK
        uuid incident_id FK
        uuid target_organization_id FK
        uuid replacement_for_id FK
        uuid creation_command_id UK
        varchar status
        timestamptz created_at
    }
    RESPONSE {
        uuid id PK
        uuid response_assignment_id FK
        uuid actor_user_id FK
        uuid command_id UK
        varchar activity_kind
        timestamptz occurred_at
    }
    INCIDENT_STATUS_HISTORY {
        uuid id PK
        uuid incident_id FK
        uuid changed_by_user_id FK
        uuid command_id UK
        varchar from_status
        varchar to_status
        timestamptz occurred_at
    }
    ASSIGNMENT_STATUS_HISTORY {
        uuid id PK
        uuid response_assignment_id FK
        uuid changed_by_user_id FK
        uuid command_id UK
        varchar from_status
        varchar to_status
        timestamptz occurred_at
    }
    NOTIFICATION {
        uuid id PK
        uuid recipient_user_id FK
        uuid incident_id FK
        uuid response_assignment_id FK
        uuid creation_command_id UK
        varchar status
        timestamptz created_at
    }
    NOTIFICATION_DELIVERY_ATTEMPT {
        uuid id PK
        uuid notification_id FK
        integer attempt_number
        varchar outcome
        timestamptz attempted_at
    }
    AUDIT_EVENT {
        uuid id PK
        uuid actor_user_id FK
        varchar actor_kind
        varchar actor_service_ref
        varchar actor_ref_snapshot
        varchar resource_type
        uuid resource_id
        varchar action
        timestamptz occurred_at
    }

    APP_USER }o--o{ AUTH_GROUP : global_roles
    AUTH_GROUP }o--o{ AUTH_PERMISSION : grants_permissions
    AUTH_GROUP ||--o{ ORGANIZATION_MEMBERSHIP : scopes_role
    APP_USER ||--o{ ORGANIZATION_MEMBERSHIP : belongs
    ORGANIZATION ||--o{ ORGANIZATION_MEMBERSHIP : has_members
    ORGANIZATION o|--o{ VIDEO_SOURCE : owns
    VIDEO_SOURCE ||--o{ DETECTION_EVENT : produces
    ACCIDENT_CANDIDATE ||--|{ CANDIDATE_DETECTION_EVENT : groups
    DETECTION_EVENT ||--o| CANDIDATE_DETECTION_EVENT : associated_once
    ACCIDENT_CANDIDATE ||--o| CANDIDATE_REVIEW : final_review
    APP_USER ||--o{ CANDIDATE_REVIEW : reviewer
    ACCIDENT_CANDIDATE ||--o| ACCIDENT_INCIDENT : verified_into
    DETECTION_EVENT o|--o{ EVIDENCE_ASSET : provenance
    EVIDENCE_ASSET ||--o{ EVIDENCE_ASSOCIATION : linked
    VIDEO_SOURCE o|--o| EVIDENCE_ASSOCIATION : controlled_input
    ACCIDENT_CANDIDATE o|--o{ EVIDENCE_ASSOCIATION : candidate_evidence
    ACCIDENT_INCIDENT o|--o{ EVIDENCE_ASSOCIATION : incident_evidence
    EVIDENCE_ASSET ||--o{ EVIDENCE_UPLOAD_SESSION : upload_attempts
    VIDEO_SOURCE o|--o{ LOCATION_RECORD : camera_subject
    VIDEO_SOURCE o|--o{ LOCATION_RECORD : source_provenance
    DETECTION_EVENT o|--o{ LOCATION_RECORD : source_provenance
    ACCIDENT_CANDIDATE o|--o{ LOCATION_RECORD : candidate_location
    ACCIDENT_INCIDENT o|--o{ LOCATION_RECORD : incident_location
    LOCATION_RECORD ||--o{ LOCATION_CORRECTION_HISTORY : corrected
    APP_USER ||--o{ LOCATION_CORRECTION_HISTORY : corrector
    ACCIDENT_INCIDENT ||--o{ RESPONSE_ASSIGNMENT : assigned
    ORGANIZATION ||--o{ RESPONSE_ASSIGNMENT : target
    RESPONSE_ASSIGNMENT o|--o| RESPONSE_ASSIGNMENT : replaces
    RESPONSE_ASSIGNMENT ||--o{ RESPONSE : activity
    APP_USER ||--o{ RESPONSE : records
    ACCIDENT_INCIDENT ||--o{ INCIDENT_STATUS_HISTORY : transitions
    RESPONSE_ASSIGNMENT ||--o{ ASSIGNMENT_STATUS_HISTORY : transitions
    APP_USER o|--o{ INCIDENT_STATUS_HISTORY : changes
    APP_USER o|--o{ ASSIGNMENT_STATUS_HISTORY : changes
    APP_USER ||--o{ NOTIFICATION : receives
    ACCIDENT_INCIDENT o|--o{ NOTIFICATION : incident_notice
    RESPONSE_ASSIGNMENT o|--o{ NOTIFICATION : assignment_notice
    NOTIFICATION ||--o{ NOTIFICATION_DELIVERY_ATTEMPT : attempts
    APP_USER o|--o{ AUDIT_EVENT : human_actor
~~~

## Relationship and Cardinality Rules

- `AUTH_GROUP` and `AUTH_PERMISSION` are Django's built-in role/permission mechanisms. A human may hold multiple groups. `OrganizationMembership` scopes a Police/Hospital group to one organization; backend object authorization also requires an active membership for the assignment target. `AI_SERVICE` is a machine principal represented only by a non-secret `service_ref`, not an `APP_USER` or group. Django's auth many-to-many join tables are framework-managed and are not custom domain entities.
- An organization can have many members and sources. A source owner organization is optional for individually owned approved sources; an opaque owner reference is required when there is no organization.
- Each DetectionEvent belongs to exactly one authorized VideoSource. A candidate has one or more distinct events; an event has zero or one candidate association. A database uniqueness rule prevents attaching one event to two candidates.
- A candidate has zero or one incident. `AccidentIncident.candidate_id` is non-null and unique, so an incident cannot exist without its verified candidate and a candidate cannot create two incidents.
- Evidence associations use three explicit nullable foreign keys, one each to a controlled VideoSource, candidate, or incident; a row must set exactly one. There is no generic content-type relationship. A controlled-file source is represented by a private EvidenceAsset and a source-level association before authorization. One asset can be associated with a source, candidate, and resulting incident through separate rows; media bytes are not duplicated.
- Location rows use explicit foreign keys for a VideoSource, candidate, incident, and provenance source event. Exactly one subject foreign key (source, candidate, or incident) is set. The current record per subject is enforced with partial unique indexes. Camera position and accident-location claims remain distinguished by `claim_kind` and `source_method`.
- A notification must reference exactly one incident or response assignment. Delivery attempts are children of notifications and never alter the referenced business state.
- Audit target resolution is the one intentional generic reference: a constrained `resource_type` plus UUID `resource_id` lets one append-only ledger cover unrelated domains. It is not used for business relationships and therefore cannot replace a foreign key elsewhere. `actor_kind` distinguishes human, machine, and unauthenticated actors; a nullable human FK may be cleared only under approved erasure while a non-secret actor snapshot preserves attribution.

## Entity Evaluation

| Proposed concept | Phase 2 decision | Reason |
|---|---|---|
| User | MVP custom Django `AbstractUser` model, configured before initial migrations | UUID key and normalized email login; disabled/anonymized rather than cascade-deleted while retained history refers to the account. |
| Role | Django `Group`/`Permission`, no domain Role table | Reuses Django grants; Police/Hospital target scope is supplied by OrganizationMembership. |
| Organization | MVP table | Represents agency/source-owner identity and active eligibility. |
| OrganizationMembership | MVP table | Scopes a human's Police/Hospital capability to one organization. |
| VideoSource | MVP table | Owns source identity, owner/authorization, health, and policy references; source credentials remain outside the database. |
| DetectionEvent | MVP table | Stores one accepted machine observation with stable source-scoped identity and model/time provenance. |
| AccidentCandidate | MVP table | Stores the potential accident's current human-review state, separate from observations and incidents. |
| CandidateDetectionEvent | MVP explicit join table | Preserves many-event provenance while ensuring one event is associated at most once. |
| CandidateReview | MVP table | Stores the one final human verification/rejection decision, reviewer, time, rationale, and retry key. |
| AccidentIncident | MVP table | Stores authoritative incident state created only after verified candidate; unique candidate link prevents duplicates. |
| EvidenceAsset | MVP table | Stores private object metadata and independent upload/validation/deletion state, never media bytes. |
| EvidenceAssociation | MVP typed association table | Links an asset to exactly one VideoSource, candidate, or incident per row using real FKs; avoids generic business polymorphism. |
| EvidenceUploadSession | MVP table | Records short-lived upload operation state and safe failure outcomes, without URLs or credentials. |
| LocationRecord | MVP table | Stores a provenance-aware source/candidate/incident location claim, distinguishing camera position from accident location. |
| LocationCorrectionHistory | MVP append-oriented history table | Preserves authorized before/after coordinate/accuracy changes and reasons. |
| ResponseAssignment | MVP table | Owns one incident-to-Police/Hospital target lifecycle; reassignment creates a linked row. |
| Response | MVP append-oriented activity table | Records simulated actor activities for exactly one assignment; it is not a second status owner. |
| IncidentStatusHistory | MVP append-oriented history table | Preserves the overall incident transition actor, reason, time, and command identity. |
| AssignmentStatusHistory | MVP append-oriented history table | Preserves each target's independent status transitions and reasons. |
| Notification | MVP table | Tracks a simulated notice for one recipient and one incident or assignment, separately from business state. |
| NotificationDeliveryAttempt | MVP append-oriented history table | Records each simulated attempt outcome without representing acknowledgement. |
| AuditEvent | MVP append-only audit ledger | Attributes security/business actions across domains without copying secrets or raw payloads. |
| AI_SERVICE machine principal | No application table or human role | Identity and credentials are managed outside domain tables; only a stable non-secret service reference is recorded. |
| Separate source-health/evidence-status history tables, refresh-token records, model-training records, legal-hold tables, spatial/PostGIS tables, notification outbox | Future only after approved need | MVP uses current health fields plus AuditEvent, no token persistence, numeric coordinates, and simulated notifications. Add explicit models only when workflow/provider/policy requirements justify them. |

See the [schema specification](database_schema_specification.md) for the physical proposal and [data dictionary](data_dictionary.md) for every proposed field.
