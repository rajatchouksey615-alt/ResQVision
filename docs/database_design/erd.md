# Conceptual Entity Relationship Design

**Status:** REVISED_DRAFT — conceptual relationships for team approval; not a physical schema.

This view separates machine observations, human-reviewed candidates, authoritative incidents, per-agency assignments, evidence media, and location provenance. Names are logical concepts only. It defines no SQL tables, Django models, field types, constraints, indexes, or migrations.

EvidenceAsset is the canonical name used here for the controlled evidence concept (called AccidentEvidence in an earlier candidate list).

## Conceptual Relationships

~~~mermaid
flowchart LR
    User[User] -->|has| Role[Role]
    VideoSource[VideoSource] -->|produces observations| Event[DetectionEvent]
    Event -->|zero or one candidate association| Candidate[AccidentCandidate]
    Candidate -->|verified decision creates at most one| Incident[AccidentIncident]
    Candidate -->|has evidence| Evidence[EvidenceAsset]
    Incident -->|references related evidence| Evidence
    Incident -->|one to many| Assignment[ResponseAssignment]
    Assignment -->|one to many| Response[Response]
    Incident -->|one to many| IHistory[IncidentStatusHistory]
    Assignment -->|one to many| AHistory[AssignmentStatusHistory]
    Assignment -->|may create| Notification[Notification]
    Incident -->|has provenance claims| Location[LocationProvenance]
    VideoSource -->|may provide camera location| Location
    Event -->|may provide source-time context| Location
    User -->|acts as| Audit[AuditEvent]
    Event -->|audit target| Audit
    Candidate -->|audit target| Audit
    Incident -->|audit target| Audit
    Assignment -->|audit target| Audit
    Evidence -->|audit target| Audit
~~~

## Concept Responsibilities and Ownership

| Concept | Responsibility | Authoritative owner | Sensitive/retention considerations |
|---|---|---|---|
| User | Human identity and account lifecycle | Backend | Identity and credentials are sensitive; password material is handled by framework security |
| Role | ADMIN, POLICE, HOSPITAL human authorization grouping | Backend | Role changes require audit |
| VideoSource | Authorized input source, owner/reference, source type, availability/health, location/time provenance, input-config, and policy references | Backend registry metadata; source owner retains source | Private footage and camera access configuration are sensitive; never store camera credentials in Git |
| DetectionEvent | One machine-generated observation, provenance, processing version/reference, and intake outcome | Backend after authenticated submission | Preserve source/time and duplicate/replay outcome; retention TBD |
| AccidentCandidate | Potential accident with one or more DetectionEvents, evidence, and review state | Backend | Candidate review and rejection retained for approved audit/evaluation policy |
| AccidentIncident | Authoritative verified accident record, created only by backend after approved human decision | Backend | Incident/location data is sensitive and access-scoped |
| EvidenceAsset | Media reference, upload/validation/availability lifecycle, and provenance | Backend owns metadata/access; object storage owns media bytes | Private by default; retention, deletion, scanning and legal hold TBD |
| ResponseAssignment | Assignment of one incident to one eligible Police or Hospital target | Backend | Each target and status is independently scoped |
| Response | Activity/status update belonging to exactly one assignment | Backend | Simulated prototype status; no treatment/dispatch implication |
| IncidentStatusHistory | Incident-level transition history | Backend | Attributable and protected from silent overwrite |
| AssignmentStatusHistory | Independent lifecycle/reassignment history per assignment | Backend | Attributable and protected from silent overwrite |
| Notification | Simulated delivery/read status related to an incident or assignment | Backend | Notification state never determines assignment acknowledgement |
| AuditEvent | Actor/service action, target, timestamp, outcome and safe context | Backend | Exclude passwords, tokens, credentials, and unnecessary raw media |
| LocationProvenance | Location origin, associated source, timestamp, uncertainty/accuracy, verification and correction history | Backend | Precise location is sensitive; do not imply camera position equals incident location |

## Relationship and Lifecycle Rules

- One VideoSource can produce many DetectionEvents. A DetectionEvent remains distinct even when linked to an AccidentCandidate.
- One AccidentCandidate may aggregate multiple DetectionEvents and EvidenceAssets. Candidate association is a separate policy from exact event-ID idempotency.
- Candidate states are RECEIVED, UNDER_REVIEW, VERIFIED, and REJECTED. Only an authorized human review can transition to VERIFIED or REJECTED.
- A verified candidate creates one linked AccidentIncident. The backend must keep candidate verification, incident creation, and history consistent in one transaction; no orphan incident or falsely verified candidate may remain after failure.
- REJECTED candidates do not create incidents and remain distinguishable for approved audit/evaluation retention.
- One AccidentIncident may have multiple ResponseAssignments, including separate Police and Hospital targets. Each assignment owns its own status/history and has one-to-many Response activity.
- IncidentStatusHistory and AssignmentStatusHistory are distinct; an assignment acknowledgement cannot become an incident-level acknowledgement.
- Notification records may relate to an assignment or incident, but delivery/read state never mutates assignment or incident state.
- EvidenceAsset may be associated with a candidate and referenced by the resulting incident without duplicating media bytes.
- LocationProvenance preserves the origin of each location claim and any authorized correction.
- AuditEvent references the acting human/service and target concept; storage design and retention remain physical-design decisions.

## Storage Boundary

PostgreSQL is planned for structured records and metadata. Object storage is intended for evidence bytes only. Backend policy controls upload and retrieval; object storage does not own business authorization. Physical normalization, identifiers, exact relationships, field types, indexes, constraints, and migrations belong to a separate approved database design.
