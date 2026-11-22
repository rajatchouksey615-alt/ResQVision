# PostgreSQL Data Dictionary

**Status:** Physical field dictionary synchronized with Django models and migrations. The local development database has these migrations applied; no production database is configured.

## Conventions

- All ResQVision-owned tables use `id uuid PRIMARY KEY`, created by Django with `uuid.uuid4`; no PostgreSQL UUID extension is required. Django-owned auth tables retain their framework key types.
- `timestamptz` values are instants and are read/written in UTC (`USE_TZ=True`). `created_at`/`updated_at` defaults below mean Django-managed `timezone.now`/auto-update behavior, not a selected database server timezone.
- `NULL` means the value is unknown/not applicable until the corresponding state requires it. Checks that span columns are detailed in [constraints and indexes](constraints_and_indexes.md).
- Finite state and vocabulary fields are bounded `varchar` with database `CHECK` constraints and corresponding application choices. Opaque policy/provider/action codes are bounded and allow-listed at the backend boundary. PostgreSQL native ENUM is not used.
- `FK` targets use `settings.AUTH_USER_MODEL` for humans. `PROTECT` is the default for retained history; actor FKs may use `SET_NULL` only where a stable actor UUID snapshot is also retained.
- “Sensitive” describes data handling, not a classification imposed by law. Roles/permissions are not a security substitute for backend object authorization.

## Django-Managed Authentication Tables

These tables are provided by Django auth and must not be duplicated. The listed key types match Django 5.2.19 migrations with the configured custom UUID user model and `DEFAULT_AUTO_FIELD=BigAutoField`. Existing Django auth migrations define Group/Permission keys as `integer` (`AutoField`); the project default does not rewrite already-defined framework migration fields.

| Table/concept | Fields and type decisions | Purpose and constraints |
|---|---|---|
| `accounts_user` / `APP_USER` | `id uuid PK`; `password varchar(128)`; `last_login timestamptz NULL`; `is_superuser boolean NOT NULL DEFAULT false`; `email varchar(254) NOT NULL UNIQUE`; `first_name varchar(150) NOT NULL DEFAULT ''`; `last_name varchar(150) NOT NULL DEFAULT ''`; `is_staff boolean NOT NULL DEFAULT false`; `is_active boolean NOT NULL DEFAULT true`; `date_joined timestamptz NOT NULL` | Custom `AbstractUser` subclass selected before the first migration; remove the inherited `username` field (`username = None`), use a custom manager, and set `USERNAME_FIELD='email'`. Normalize email to trimmed lowercase. `is_active=false` disables authentication; ordinary account removal is deactivation/anonymization, not cascade deletion. `is_superuser` is tightly controlled and never inferred from an app role. Password is Django's encoded hash only. Do not add raw tokens, response data, or source credentials. |
| `auth_group` / Role | `id integer PK`; `name varchar(150) NOT NULL UNIQUE` | Django Group is the role catalog. Seed the stable group names `ADMIN`, `POLICE`, `HOSPITAL`; do not create a second Role table. |
| `auth_permission`, `auth_group_permissions` | `auth_permission.id integer`; `content_type_id integer`; `auth_group_permissions.group_id integer`, `permission_id integer`; unique group/permission pair | Django permissions define action capabilities; object/organization scope remains a backend authorization check. |
| `accounts_user_groups`, `accounts_user_user_permissions` | User FK is UUID; Group/Permission FK is integer; unique pairs | Framework-managed M2M relations. Do not manually create parallel join tables. |

## Organization and Membership

### `organizations_organization`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Stable organization identity; internal. |
| `code` | `varchar(80)` | No / none | Unique | Stable normalized code; trim, case-normalize, no empty value. Internal. |
| `display_name` | `varchar(200)` | No / none | — | Human-readable name; validate non-empty. Internal. |
| `organization_kind` | `varchar(24)` | No / none | Check | `POLICE`, `HOSPITAL`, `SOURCE_OWNER`, or `OTHER`; not an operational/emergency integration. |
| `is_active` | `boolean` | No / `true` | `(organization_kind, is_active)` | Disables new memberships/assignments while preserving history. |
| `created_at` | `timestamptz` | No / Django timestamp | — | Creation instant in UTC. |
| `updated_at` | `timestamptz` | No / Django timestamp | — | Last metadata change in UTC. |

### `organizations_membership`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Membership identity. |
| `user_id` | `uuid` | No / none | FK `accounts_user`, PROTECT | Human account. Sensitive identity relation. |
| `organization_id` | `uuid` | No / none | FK `organizations_organization`, PROTECT | Organization scope. |
| `role_group_id` | `integer` | No / none | FK `auth_group`, PROTECT | Django 5.2.19 Group uses its migration-defined `AutoField`; role group is scoped to this organization and must be `POLICE` or `HOSPITAL` in this table. |
| `status` | `varchar(16)` | No / `ACTIVE` | Check; `(organization_id, role_group_id, status)` | `ACTIVE`, `SUSPENDED`, `REVOKED`; access requires ACTIVE and active organization/user. |
| `created_at` | `timestamptz` | No / Django timestamp | — | Membership creation; role changes are audited. |
| `updated_at` | `timestamptz` | No / Django timestamp | — | Last membership state change. |

Unique: `(user_id, organization_id, role_group_id)`. One person may have multiple roles and multiple memberships. Do not create membership rows for the global `ADMIN` group.
Police/Hospital access requires both the corresponding Django Group grant and an ACTIVE membership for the target organization, plus active user/organization records. Membership alone never grants global role capability.

## Video Source and Detection

### `sources_video_source`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Internal source identity. |
| `source_code` | `varchar(128)` | No / none | Unique | Server-managed stable source identifier; never use a camera URL or credential. |
| `name` | `varchar(200)` | No / none | — | Operator-facing label; avoid embedding private owner/contact information. |
| `source_type` | `varchar(24)` | No / none | Check | `CONTROLLED_FILE`, `CAMERA_STREAM`, or `OTHER`; enabled types require approved input policy. |
| `owner_organization_id` | `uuid` | Yes / NULL | FK Organization, PROTECT | Owning organization when available. Sensitive relationship. |
| `owner_external_ref` | `varchar(128)` | Yes / NULL | — | Opaque owner reference when no organization row exists; no email/phone. At least one owner reference is required. |
| `authorization_status` | `varchar(20)` | No / `PENDING_REVIEW` | Check; `(authorization_status, availability_status)` | `PENDING_REVIEW`, `AUTHORIZED`, `SUSPENDED`, `REVOKED`. Only AUTHORIZED sources can produce accepted events. |
| `availability_status` | `varchar(16)` | No / `UNKNOWN` | `(availability_status, last_health_check_at)` | `UNKNOWN`, `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`; operational signal, not authorization. |
| `authorized_by_user_id` | `uuid` | Yes / NULL | FK User, PROTECT | Human approver; required with `authorized_at` for AUTHORIZED status. Sensitive audit link. |
| `authorized_at` | `timestamptz` | Yes / NULL | — | Authorization instant; paired with authorizing user. |
| `authorization_reference` | `varchar(256)` | Yes / NULL | — | Opaque reference to permission/consent evidence; no document contents. Sensitive reference. |
| `configuration_ref` | `varchar(256)` | Yes / NULL | — | Non-secret reference to protected runtime configuration/secret manager; never a connection string or password. Restricted. |
| `processing_policy_ref` | `varchar(100)` | No / none | — | Stable approved purpose/processing policy code. |
| `retention_policy_ref` | `varchar(100)` | No / none | — | Policy code used to govern source-derived data; duration remains institutionally approved. |
| `last_health_check_at` | `timestamptz` | Yes / NULL | `(availability_status, last_health_check_at)` | Most recent health signal; no check result history table in MVP. |
| `created_at` | `timestamptz` | No / Django timestamp | — | Registry creation. |
| `updated_at` | `timestamptz` | No / Django timestamp | — | Registry update; authorization changes also generate AuditEvent. |

For `source_type=CONTROLLED_FILE`, authorization for processing requires one source-level EvidenceAssociation to an `AVAILABLE` private EvidenceAsset. Register each controlled uploaded file as its own VideoSource; a live camera source does not require this source-file association.

### `detection_detection_event`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Internal immutable observation identity. |
| `video_source_id` | `uuid` | No / none | FK VideoSource, PROTECT; `(video_source_id, detected_at)` | Authorized source that produced the observation. |
| `external_event_id` | `varchar(128)` | No / none | Unique with source | Stable AI submission identity; idempotency scope is one source. |
| `service_principal_ref` | `varchar(128)` | No / none | — | Non-secret authenticated machine identity reference, normally `AI_SERVICE`. |
| `model_name` | `varchar(100)` | No / none | — | Model family/name; internal provenance. |
| `model_version` | `varchar(100)` | No / none | — | Model/version reference; no weights stored in PostgreSQL. |
| `detected_at` | `timestamptz` | No / none | `(video_source_id, detected_at)` | Source/event instant in UTC; source clock uncertainty belongs in metadata. |
| `received_at` | `timestamptz` | No / Django timestamp | `(received_at)` | Backend acceptance time; immutable. |
| `processing_outcome` | `varchar(20)` | No / none | Check | `OBSERVATION` or `UNCERTAIN`; a DetectionEvent represents an observation. No-observation and processing-failure outcomes do not create DetectionEvent rows. Neither value means a verified incident. |
| `confidence` | `numeric(5,4)` | Yes / NULL | — | Optional model score in `[0,1]`; not a verification decision. |
| `payload_sha256` | `varchar(64)` | Yes / NULL | — | Optional lowercase SHA-256 digest of the accepted canonical event payload; no raw media. |
| `metadata_schema_version` | `smallint` | No / `1` | — | Version for auxiliary event metadata. |
| `auxiliary_metadata` | `jsonb` | No / `{}` | — | Versioned model-specific, non-core metadata only; object shape/size allow-listed by application. Sensitive if it contains location hints. |

Unique: `(video_source_id, external_event_id)`. A retry returns the existing event result. A rejected submission without an accepted event is recorded as a safe AuditEvent/outcome, not as a fake accepted DetectionEvent. Duplicate-attempt audit does not create a second event row.

## Candidate and Incident

### `incidents_accident_candidate`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Candidate identity; distinct from event and incident identifiers. |
| `police_organization_id` | `uuid` | Yes / NULL | FK Organization, PROTECT | Backend-bound Police jurisdiction. Legacy rows may remain null; new reviewer assignments require an active Police organization. |
| `status` | `varchar(20)` | No / `RECEIVED` | Check; `(status, created_at)` | `RECEIVED`, `UNDER_REVIEW`, `VERIFIED`, `REJECTED`. Current candidate state only. |
| `created_at` | `timestamptz` | No / Django timestamp | `(status, created_at)` | Candidate creation instant. |
| `updated_at` | `timestamptz` | No / Django timestamp | — | Last current-state update. |

At least one `CandidateDetectionEvent` association must exist before the candidate is placed in review. Enforce with the candidate-association transaction, because a row CHECK cannot enforce a child-row count.

### `incidents_candidate_reviewer_assignment`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Immutable assignment record identity. |
| `candidate_id` | `uuid` | No / none | FK Candidate, PROTECT, UNIQUE | One initial assignment record per candidate. No historical rows are backfilled. |
| `police_organization_id` | `uuid` | No / none | FK Organization, PROTECT; `(police_organization_id, assigned_at)` | Candidate's active Police organization at assignment time. |
| `reviewer_id` | `uuid` | No / none | FK User, PROTECT; `(reviewer_id, assigned_at)` | Active Police reviewer selected for the candidate. |
| `assigned_by_user_id` | `uuid` | No / none | FK User, PROTECT | Active ADMIN-group assigner with active membership in the candidate Police organization. |
| `command_id` | `uuid` | No / none | UNIQUE | Idempotency key for assignment retries. |
| `assigned_at` | `timestamptz` | No / Django timestamp | — | Assignment instant in UTC; the row is append-only. |

Assignment creation and its `CANDIDATE_REVIEWER_ASSIGNED` AuditEvent commit together. The one-to-one candidate key and candidate row lock prevent concurrent duplicate assignments. The migration creates the table only and does not assign existing candidates.

### `incidents_candidate_detection_event`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Association identity. |
| `candidate_id` | `uuid` | No / none | FK Candidate, PROTECT; `(candidate_id, linked_at)` | Candidate receiving the observation. |
| `detection_event_id` | `uuid` | No / none | FK DetectionEvent, PROTECT; UNIQUE | Each event belongs to at most one candidate. |
| `association_method` | `varchar(20)` | No / none | Check | `RULE_BASED`, `REVIEWER_CONFIRMED`, or `MANUAL`; grouping policy stays explicit. |
| `linked_by_user_id` | `uuid` | Yes / NULL | FK User, PROTECT | Required for manual/reviewer-confirmed association; NULL for backend rule association. |
| `linked_at` | `timestamptz` | No / Django timestamp | `(candidate_id, linked_at)` | Association instant. |

The pair `(candidate_id, detection_event_id)` is also unique; the stronger unique `detection_event_id` rule enforces the current one-candidate-per-event policy.

### `incidents_candidate_review`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Final review decision identity. |
| `candidate_id` | `uuid` | No / none | FK Candidate, PROTECT; UNIQUE | One final review outcome per candidate under MVP no-reopen policy. This is an ordinary unique constraint because the field is non-null. |
| `reviewer_id` | `uuid` | No / none | FK User, PROTECT; `(reviewer_id, reviewed_at)` | Authorized human reviewer; never AI_SERVICE. |
| `decision` | `varchar(12)` | No / none | Check | `VERIFIED` or `REJECTED`; candidate's current status is synchronized in the same transaction. |
| `rationale` | `text` | Yes / NULL | — | Required and non-blank for REJECTED; concise decision reason, no unnecessary personal data. Sensitive. |
| `reviewed_at` | `timestamptz` | No / Django timestamp | `(reviewed_at)` | Final decision instant. |
| `command_id` | `uuid` | Yes / NULL | UNIQUE when present | Client/request idempotency key for safe decision retry. |

### `incidents_accident_incident`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Authoritative incident identity. |
| `candidate_id` | `uuid` | No / none | FK Candidate, PROTECT, UNIQUE | Exactly one verified candidate per incident; prevents duplicate incident creation. |
| `status` | `varchar(20)` | No / `OPEN` | Check; `(status, created_at)` | `OPEN`, `RESPONSE_ACTIVE`, `RESOLVED`, `CLOSED`; no assignment state here. |
| `created_at` | `timestamptz` | No / Django timestamp | `(created_at)` | Created atomically with candidate verification. |
| `updated_at` | `timestamptz` | No / Django timestamp | — | Current record update instant. |

Resolution/closure actor, reason and time are retained in IncidentStatusHistory rather than duplicated as incident columns. Severity is omitted until an approved, testable scale exists.

## Evidence and Upload Coordination

### `evidence_evidence_asset`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Logical private media identity. |
| `source_detection_event_id` | `uuid` | Yes / NULL | FK DetectionEvent, PROTECT | Event provenance; may be null while an AI-created upload is prepared before event acceptance and for human-added evidence. Bind it once to the accepted event during ingestion. |
| `created_by_service_ref` | `varchar(128)` | Yes / NULL | — | Non-secret service actor; pair with created-by-user so exactly one creator is set. |
| `created_by_user_id` | `uuid` | Yes / NULL | FK User, PROTECT | Human-added evidence creator. |
| `storage_provider` | `varchar(40)` | No / none | Part of unique object reference | Provider adapter code; provider selection remains open. |
| `storage_namespace` | `varchar(120)` | No / none | Part of unique object reference | Opaque private bucket/container namespace, not credentials. |
| `object_key` | `varchar(512)` | No / server-generated | Unique with provider/namespace | Unpredictable, server-controlled object identity; never user-selected path or public URL. Restricted. |
| `original_filename` | `varchar(255)` | Yes / NULL | — | Sanitized display metadata only; can contain sensitive information. |
| `media_type` | `varchar(127)` | Yes / NULL | — | Validated detected MIME type; allow-list enforced by backend. |
| `size_bytes` | `bigint` | Yes / NULL | Check `> 0` | Actual byte count; required before AVAILABLE; enforce configured limit in backend. |
| `checksum_sha256` | `varchar(64)` | Yes / NULL | Format check | Lowercase SHA-256 of object bytes; required before AVAILABLE. |
| `status` | `varchar(20)` | No / `PENDING_UPLOAD` | Check; `(status, created_at)` | `PENDING_UPLOAD`, `UPLOADING`, `QUARANTINED`, `AVAILABLE`, `FAILED`, `EXPIRED`, `DELETED`. |
| `scan_status` | `varchar(16)` | No / `PENDING` | Check | `PENDING`, `NOT_REQUIRED`, `PASSED`, `FAILED`; AVAILABLE requires NOT_REQUIRED or PASSED. |
| `validation_completed_at` | `timestamptz` | Yes / NULL | — | Required before AVAILABLE; backend has completed applicable validation. |
| `uploaded_at` | `timestamptz` | Yes / NULL | — | Object upload completion time; not availability by itself. |
| `retention_policy_ref` | `varchar(100)` | No / none | — | Applied policy code, no invented duration. |
| `created_at` | `timestamptz` | No / Django timestamp | `(status, created_at)` | Asset metadata creation time. |
| `expired_at` | `timestamptz` | Yes / NULL | — | Time access was disabled for retention/expiry. |
| `deleted_at` | `timestamptz` | Yes / NULL | — | Time object deletion was confirmed; metadata remains as a tombstone. |

An AI-created asset may be prepared/uploaded before its DetectionEvent is accepted, so its event FK may initially be null. The authenticated event-ingestion transaction binds the supplied asset ID to that event once. A candidate does not enter review until the required associated EvidenceAssets are AVAILABLE and validated.

### `evidence_evidence_association`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Explicit relation identity. |
| `evidence_asset_id` | `uuid` | No / none | FK EvidenceAsset, PROTECT | Private asset being related. |
| `video_source_id` | `uuid` | Yes / NULL | FK VideoSource, PROTECT; partial UNIQUE | Source-level media link; at most one source-input EvidenceAsset per controlled-file VideoSource. |
| `candidate_id` | `uuid` | Yes / NULL | FK Candidate, PROTECT; partial unique | Candidate association when set. |
| `incident_id` | `uuid` | Yes / NULL | FK Incident, PROTECT; partial unique | Incident association when set. |
| `associated_by_user_id` | `uuid` | Yes / NULL | FK User, PROTECT | Human association actor; absent for backend-created candidate evidence. |
| `created_at` | `timestamptz` | No / Django timestamp | — | Association creation instant. |

Exactly one of `video_source_id`, `candidate_id`, and `incident_id` is set. A controlled uploaded VideoSource must be associated with one AVAILABLE private source-video EvidenceAsset before it is authorized for processing. Each controlled-file upload has its own VideoSource row. The same asset may also be linked to a candidate and resulting incident using separate rows; media bytes are not duplicated.

### `evidence_evidence_upload_session`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Opaque operation/session identifier. |
| `evidence_asset_id` | `uuid` | No / none | FK EvidenceAsset, PROTECT | Asset being uploaded; the FK index supports its session history. |
| `service_ref` | `varchar(128)` | No / none | — | Authenticated non-secret service principal reference. |
| `status` | `varchar(16)` | No / `CREATED` | Check; partial unique active session per asset | `CREATED`, `AUTHORIZED`, `UPLOADING`, `COMPLETED`, `FAILED`, `EXPIRED`, `REVOKED`. |
| `authorized_at` | `timestamptz` | Yes / NULL | — | Authorization grant issue time. |
| `expires_at` | `timestamptz` | No / none | `(status, expires_at)` | Short expiry; require `expires_at > created_at`. |
| `completed_at` | `timestamptz` | Yes / NULL | — | Completion report time; asset still requires backend validation. |
| `failure_code` | `varchar(64)` | Yes / NULL | — | Safe allow-listed error code only; no credentials, signed URL, or raw provider response. |
| `created_at` | `timestamptz` | No / Django timestamp | — | Session creation instant. |

Never store signed upload URLs, bearer tokens, multipart secrets, storage credentials, or arbitrary object paths in this table. A new session is created for each retry.

## Location and Correction History

### `locations_location_record`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | One provenance-aware location claim. |
| `subject_video_source_id` | `uuid` | Yes / NULL | FK VideoSource, PROTECT; unique current partial index | Camera position associated with this source when subject is a source. |
| `subject_candidate_id` | `uuid` | Yes / NULL | FK Candidate, PROTECT; unique current partial index | Candidate-level accident-location claim. |
| `subject_incident_id` | `uuid` | Yes / NULL | FK Incident, PROTECT; unique current partial index | Incident-level accident-location claim. |
| `source_video_source_id` | `uuid` | Yes / NULL | FK VideoSource, PROTECT | Source camera provenance for a location claim. |
| `source_detection_event_id` | `uuid` | Yes / NULL | FK DetectionEvent, PROTECT | Event provenance for GPS/inferred location. |
| `claim_kind` | `varchar(20)` | No / none | Check | `CAMERA_POSITION` or `ACCIDENT_LOCATION`; never conflate the two. |
| `source_method` | `varchar(16)` | No / none | Check | `CAMERA`, `GPS`, `INFERRED`, or `MANUAL`. |
| `latitude` | `numeric(9,6)` | Yes / NULL | Range check | WGS84 latitude `[-90,90]`; NULL allowed only when coordinates are unknown. Sensitive. |
| `longitude` | `numeric(9,6)` | Yes / NULL | Range check | WGS84 longitude `[-180,180]`; must be null/non-null with latitude. Sensitive. |
| `accuracy_m` | `numeric(10,2)` | Yes / NULL | Check `>= 0` | Accuracy/uncertainty in metres; nullable if not supplied. Do not fabricate. |
| `captured_at` | `timestamptz` | Yes / NULL | — | Source measurement time; nullable if unavailable, not substituted with database time. |
| `verification_status` | `varchar(16)` | No / `UNVERIFIED` | Check | `UNVERIFIED`, `VERIFIED`, `CORRECTED`. |
| `verified_by_user_id` | `uuid` | Yes / NULL | FK User, PROTECT | Human verifier; paired with verified_at. |
| `verified_at` | `timestamptz` | Yes / NULL | — | Verification instant, paired with verifier. |
| `created_by_user_id` | `uuid` | Yes / NULL | FK User, PROTECT | Human creator when manually supplied. |
| `created_by_service_ref` | `varchar(128)` | Yes / NULL | — | Non-secret machine creator reference. Exactly one creator identity is set. |
| `is_current` | `boolean` | No / `true` | Partial unique by subject | Current claim for that subject; superseded records remain for provenance. |
| `created_at` | `timestamptz` | No / Django timestamp | — | Claim creation time. |

Exactly one subject FK is set. Source references describe provenance, not ownership. For `CAMERA_POSITION`, source and subject identify the camera; an accident-location claim may cite a camera or event as its origin while retaining `claim_kind=ACCIDENT_LOCATION` and uncertainty.

### `locations_location_correction_history`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Immutable correction event. |
| `location_record_id` | `uuid` | No / none | FK LocationRecord, PROTECT; `(location_record_id, corrected_at)` | Corrected claim. |
| `corrected_by_user_id` | `uuid` | No / none | FK User, PROTECT; `(corrected_by_user_id, corrected_at)` | Authorized human correction actor. |
| `previous_latitude` | `numeric(9,6)` | Yes / NULL | — | Before-value; latitude/longitude pair validation. Sensitive. |
| `previous_longitude` | `numeric(9,6)` | Yes / NULL | — | Before-value. Sensitive. |
| `new_latitude` | `numeric(9,6)` | Yes / NULL | — | After-value; latitude/longitude pair validation. Sensitive. |
| `new_longitude` | `numeric(9,6)` | Yes / NULL | — | After-value. Sensitive. |
| `previous_accuracy_m` | `numeric(10,2)` | Yes / NULL | — | Before uncertainty. Sensitive. |
| `new_accuracy_m` | `numeric(10,2)` | Yes / NULL | — | After uncertainty. Sensitive. |
| `reason` | `text` | No / none | — | Non-blank correction rationale, minimum necessary. Sensitive. |
| `corrected_at` | `timestamptz` | No / Django timestamp | — | Correction instant; append-only. |

LocationCorrectionHistory captures coordinate/accuracy changes. If the source method, captured time, claim kind, or verification status changes, create a new LocationRecord, mark the prior claim non-current, and retain both rows rather than changing unrecorded provenance fields in place.

## Assignment, Response and History

### `responses_response_assignment`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | One agency-target assignment. |
| `incident_id` | `uuid` | No / none | FK Incident, PROTECT; `(incident_id, status)` | Verified incident being assigned. |
| `target_organization_id` | `uuid` | No / none | FK Organization, PROTECT; `(target_organization_id, status, created_at)` | Eligible active Police/Hospital organization; validate organization kind and scope. |
| `assigned_by_user_id` | `uuid` | No / none | FK User, PROTECT | Authorized assignment actor. |
| `replacement_for_id` | `uuid` | Yes / NULL | Self FK, PROTECT, UNIQUE | Prior cancelled assignment; replacement must be for same incident, checked transactionally. |
| `creation_command_id` | `uuid` | Yes / NULL | UNIQUE when present | Client command idempotency key; retries return the original assignment even if its state has since changed. |
| `status` | `varchar(24)` | No / `PENDING` | Check; partial unique active target | `PENDING`, `ACKNOWLEDGED`, `IN_PROGRESS`, `COMPLETED`, `UNABLE_TO_RESPOND`, `CANCELLED`, `EXPIRED`. |
| `created_at` | `timestamptz` | No / Django timestamp | `(incident_id, created_at)` | Assignment creation; status history starts at PENDING. |
| `updated_at` | `timestamptz` | No / Django timestamp | — | Last current status/update time. |

Only one nonterminal assignment per incident and target organization is allowed at a time. Reassignment cancels the prior assignment and creates a linked row; it never changes the prior target in place.

### `responses_response`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Append-only response activity. |
| `response_assignment_id` | `uuid` | No / none | FK Assignment, PROTECT; `(response_assignment_id, occurred_at)` | Exactly one agency assignment. |
| `actor_user_id` | `uuid` | No / none | FK User, PROTECT | Human assigned-target actor. |
| `activity_kind` | `varchar(24)` | No / none | Check | `PROGRESS_UPDATE`, `READINESS_UPDATE`, `COMPLETION_NOTE`, `UNABLE_TO_RESPOND_NOTE`, `GENERAL_NOTE`. |
| `details` | `varchar(2000)` | Yes / NULL | — | Minimal simulated activity detail; no patient data or unsupported treatment claims. Sensitive. |
| `command_id` | `uuid` | Yes / NULL | UNIQUE when present | Client command idempotency key for a retried activity submission. |
| `occurred_at` | `timestamptz` | No / Django timestamp | `(response_assignment_id, occurred_at)` | Activity instant. |
| `created_at` | `timestamptz` | No / Django timestamp | — | Backend persistence time. |

`Response` stores activity, not a second current assignment state. Assignment transitions are stored in AssignmentStatusHistory.

### `incidents_incident_status_history`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Transition history row. |
| `incident_id` | `uuid` | No / none | FK Incident, PROTECT; `(incident_id, occurred_at)` | Incident transitioned. |
| `from_status` | `varchar(20)` | Yes / NULL | Check | NULL only for creation; otherwise prior incident state. |
| `to_status` | `varchar(20)` | No / none | Check | `OPEN`, `RESPONSE_ACTIVE`, `RESOLVED`, or `CLOSED`. |
| `changed_by_user_id` | `uuid` | Yes / NULL | FK User, PROTECT | Human actor when user-initiated. |
| `actor_service_ref` | `varchar(128)` | Yes / NULL | — | Non-secret system/service actor for backend transition. Exactly one actor reference is set. |
| `reason` | `text` | Yes / NULL | — | Required for RESOLVED/CLOSED and approved overrides; minimum necessary. |
| `command_id` | `uuid` | Yes / NULL | UNIQUE when present | Idempotency key for the transition command. |
| `occurred_at` | `timestamptz` | No / Django timestamp | `(incident_id, occurred_at)` | Transition instant. |

The first transition is `NULL -> OPEN`; current state and history row are committed together. Allowed transition graph and cross-assignment resolution guard are described in [transaction design](transaction_and_integrity_design.md).

### `responses_assignment_status_history`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Assignment transition history row. |
| `response_assignment_id` | `uuid` | No / none | FK Assignment, PROTECT; `(response_assignment_id, occurred_at)` | Target-specific assignment. |
| `from_status` | `varchar(24)` | Yes / NULL | Check | NULL only for initial PENDING. |
| `to_status` | `varchar(24)` | No / none | Check | Proposed assignment status vocabulary. |
| `changed_by_user_id` | `uuid` | Yes / NULL | FK User, PROTECT | Assigned user or authorized administrator. |
| `actor_service_ref` | `varchar(128)` | Yes / NULL | — | Backend actor for approved expiration; exactly one actor reference is set. |
| `reason` | `text` | Yes / NULL | — | Required for UNABLE_TO_RESPOND, CANCELLED, EXPIRED, and override. Sensitive. |
| `command_id` | `uuid` | Yes / NULL | UNIQUE when present | Idempotency key for transition retry. |
| `occurred_at` | `timestamptz` | No / Django timestamp | `(response_assignment_id, occurred_at)` | Transition instant. |

## Notifications and Audit

### `notifications_notification`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Simulated notification identity. |
| `recipient_user_id` | `uuid` | No / none | FK User, PROTECT; `(recipient_user_id, status, created_at)` | Authorized recipient. Sensitive. |
| `incident_id` | `uuid` | Yes / NULL | FK Incident, PROTECT; partial index | Incident-level notice target. |
| `response_assignment_id` | `uuid` | Yes / NULL | FK Assignment, PROTECT; partial index | Assignment-level notice target. |
| `status` | `varchar(24)` | No / `CREATED` | Check; recipient/status index | `CREATED`, `PENDING`, `DELIVERED_SIMULATED`, `FAILED`, `READ`, `CANCELLED`. |
| `creation_command_id` | `uuid` | Yes / NULL | UNIQUE when present | Idempotency key so retrying notification creation does not create a duplicate. |
| `created_at` | `timestamptz` | No / Django timestamp | `(recipient_user_id, status, created_at)` | Creation time. |
| `read_at` | `timestamptz` | Yes / NULL | — | Present iff status READ; read never acknowledges an assignment. |
| `safe_message_code` | `varchar(64)` | No / none | — | Template/message code only; no sensitive media, broad incident payload, or external delivery token. |

Exactly one of `incident_id` and `response_assignment_id` is set.

### `notifications_delivery_attempt`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Attempt identity. |
| `notification_id` | `uuid` | No / none | FK Notification, PROTECT; UNIQUE with attempt number | Parent simulated notification. |
| `attempt_number` | `integer` | No / positive | Unique with notification | One-based monotonically increasing attempt number. |
| `outcome` | `varchar(24)` | No / none | Check | `DELIVERED_SIMULATED`, `FAILED`, or `CANCELLED`; never real dispatch. |
| `attempted_at` | `timestamptz` | No / Django timestamp | `(notification_id, attempted_at)` | Simulated attempt instant. |
| `safe_failure_code` | `varchar(64)` | Yes / NULL | — | Allow-listed safe code; no stack trace or provider secrets. |
| `created_at` | `timestamptz` | No / Django timestamp | — | Persisted attempt record time. |

### `audit_audit_event`

| Field | PostgreSQL type | Null / default | Key / index | Meaning, validation and sensitivity |
|---|---|---|---|---|
| `id` | `uuid` | No / Django UUIDv4 | PK | Audit record identity. |
| `actor_user_id` | `uuid` | Yes / NULL | FK User, SET_NULL; `(actor_user_id, occurred_at)` | Human actor where applicable. Stable actor UUID snapshot is retained separately if a user is later anonymized. |
| `actor_kind` | `varchar(12)` | No / none | Check | `HUMAN`, `MACHINE`, or `ANONYMOUS`; distinguishes retained human attribution, a machine principal, or an unauthenticated attempt. |
| `actor_service_ref` | `varchar(128)` | Yes / NULL | `(actor_service_ref, occurred_at)` | Non-secret machine/service principal; required only for MACHINE actors. |
| `resource_type` | `varchar(32)` | No / none | `(resource_type, resource_id, occurred_at)` | Fixed allow-list: `USER`, `ORGANIZATION`, `MEMBERSHIP`, `VIDEO_SOURCE`, `DETECTION_EVENT`, `CANDIDATE`, `INCIDENT`, `ASSIGNMENT`, `EVIDENCE`, `LOCATION`, `NOTIFICATION`, `AUTHENTICATION`. |
| `resource_id` | `uuid` | Yes / NULL | `(resource_type, resource_id, occurred_at)` | UUID of target where one exists; authentication and unaccepted ingestion attempts with no canonical target may have no resource ID. Generic reference is audit-only and has no FK. |
| `action` | `varchar(80)` | No / none | `(action, occurred_at)` | Stable allow-listed event code. |
| `outcome` | `varchar(16)` | No / none | Check | `SUCCESS`, `DENIED`, `FAILED`, or `SIMULATED`. |
| `actor_ref_snapshot` | `varchar(128)` | No / none | — | Stable non-secret actor reference. For a human this is an opaque UUID-like account reference, retained if `actor_user_id` is nulled for approved erasure; for a machine it matches the service reference; for an unauthenticated attempt it is `ANONYMOUS`. No email/token. |
| `request_id` | `uuid` | Yes / NULL | `(request_id)` | Correlates multiple records from one operation; not a credential. |
| `context_schema_version` | `smallint` | No / `1` | — | Version of permitted context fields. |
| `safe_context` | `jsonb` | No / `{}` | — | Allow-listed non-secret metadata only; never credentials, raw request bodies, signed URLs or raw media. |
| `occurred_at` | `timestamptz` | No / Django `timezone.now` | `(occurred_at)` | Audit event instant in UTC. Append-only under application DB role. |

Database roles used by the application should have INSERT/SELECT but no UPDATE/DELETE permission on this table. A human audit row has `actor_kind=HUMAN`, no service reference, and either a user FK or a non-blank snapshot if an approved erasure nulled the FK. A machine row has `actor_kind=MACHINE`, a non-null service reference, and no user FK. An unauthenticated attempt has `actor_kind=ANONYMOUS`, no actor FK/service reference, and may use `request_id` for correlation without retaining the submitted identity string. Migrations/owner privileges remain operationally controlled; this is protection against ordinary application mutation, not a claim of tamper-proofing.

## Fields Intentionally Not Modeled

- No password plaintext, JWT/access/refresh token, API key, camera password, storage credential, signed media URL, or raw video/image field.
- No severity, treatment, dispatch, responder GPS, patient data, or emergency outcome fields without approved requirements and lawful data scope.
- No duplicated event list, candidate event array, agency status columns, notification-derived acknowledgement, or unconstrained JSON object for relational fields.
- No PostgreSQL ENUM, PostGIS geometry, video bytes in PostgreSQL, or provider-specific credentials in schema.
