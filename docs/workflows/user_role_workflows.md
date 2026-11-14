# User Role Workflows

**Status:** REVISED_DRAFT — pending team approval. See the [role-permission matrix](../requirements/role_permission_matrix.md).

## Common Authentication and Access

1. User submits credentials through the mobile client.
2. Backend authenticates and returns the approved session/token behavior (lifecycle TBD).
3. Backend determines human role, object scope, assignment target, operation, and current lifecycle state for each request; client navigation is not an access control.
4. User sees only authorized incidents, candidate/evidence detail, and that user's agency assignment. Denied requests do not disclose protected object details.
5. Logout clears the client session; token revocation and local cache behavior are TBD.

## ADMIN Workflow

~~~mermaid
flowchart TD
    A[Authenticate] --> B{Admin permission valid?}
    B -- No --> X[Access denied and safe error]
    B -- Yes --> C[View admin dashboard]
    C --> D{Choose action}
    D --> E[Manage users and roles]
    D --> F[Review VideoSource authorization and candidate queue]
    F --> G[Inspect DetectionEvents, EvidenceAssets and LocationProvenance]
    G --> H{Verification permission approved?}
    H -- No --> I[Refer to designated reviewer]
    H -- Yes --> J[Record candidate VERIFIED or REJECTED with rationale]
    J --> K[Backend creates incident only on VERIFIED]
    K --> L[Create separate target assignments if permitted]
    C --> M[Inspect permitted reports/audit]
    E --> Z[Backend validates and audits]
    J --> Z
    L --> Z
    M --> Z
~~~

Admin account/role administration is proposed within least privilege. Candidate review, VideoSource approval, assignment, reassignment/cancellation, incident resolution, and closure depend on explicit permission; the team must approve these authorities and evidence/audit scope. Admin does not receive blanket media access or dispatch authority.

## POLICE Workflow

1. Authenticate and load only the user's Police ResponseAssignments.
2. Open one assignment and review its linked incident summary, authorized evidence, and location provenance.
3. Move that assignment from PENDING to ACKNOWLEDGED; this does not acknowledge the incident or Hospital assignment.
4. Record own simulated Response activity, progress, COMPLETED, or UNABLE_TO_RESPOND with reason as permitted.
5. Review the Police assignment and scoped incident histories; log out.

Out-of-scope reads, changing Hospital state, administrative changes, and invalid/stale transitions are denied. Police activity is simulated and cannot trigger real dispatch.

## HOSPITAL Workflow

1. Authenticate and load only the user's Hospital ResponseAssignments.
2. Review the minimum incident information, authorized evidence, and location provenance needed for simulated readiness.
3. Move that assignment from PENDING to ACKNOWLEDGED; this does not acknowledge the incident or Police assignment.
4. Record own simulated readiness/Response activity, progress, COMPLETED, or UNABLE_TO_RESPOND with reason as permitted.
5. Review the Hospital assignment and scoped incident histories; log out.

Hospital users do not administer users or access unrelated evidence. Permitted details, readiness states, and incident scope remain subject to privacy and team review.

## AI Service Workflow

The AI service uses a separate AI_SERVICE machine identity; it is not an Admin/Police/Hospital user. It may submit DetectionEvents, request backend-scoped EvidenceAsset upload authorization, upload only the authorized object, and report completion. It cannot verify/reject, create an AccidentIncident, create assignments, acknowledge/update/resolve responses, browse unrelated media/user data, administer users, or contact emergency services.

## Independent Incident and Assignment Views

- Incident status is OPEN, RESPONSE_ACTIVE, RESOLVED, or CLOSED.
- Each Police/Hospital ResponseAssignment has its own PENDING, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, UNABLE_TO_RESPOND, CANCELLED, or policy-approved EXPIRED state.
- The client displays both layers; it never derives incident acknowledgement from assignment state or notification delivery.
- A non-acknowledged assignment shows an overdue/manual-follow-up indicator only under the proposed default; no timeout interval or escalation is implied.
- Incident resolution requires an authorized incident-level decision after assignment outcomes are terminal under the proposed rule. Resolution and closure are separate.

## Failure and Exception Paths

- Expired/invalid credentials: deny protected access and show a safe retry path.
- Role/scope mismatch: deny action and do not reveal whether another incident exists.
- Candidate has been rejected: show REJECTED to authorized reviewers; no AccidentIncident or assignment is created.
- Candidate/incident transaction fails: do not show a verified candidate or orphan incident; allow safe retry.
- Evidence is PENDING_UPLOAD, UPLOADING, QUARANTINED, FAILED, EXPIRED, or DELETED: deny retrieval and show state-specific unavailable outcome.
- Evidence unavailable: preserve candidate/incident visibility and mark evidence unavailable.
- Notification read/delivery: do not mark assignment acknowledged.
- One agency assignment is pending/unable/completed: show its state independently; do not mutate the other agency.
- Location is missing/uncertain: disclose the source/uncertainty and do not fabricate incident coordinates.
- Backend/network failure: show retryable status without claiming a state change succeeded.
- Stale or invalid state: reject the transition and refresh current state.
- Simulated notification failure: record/report the simulation outcome; never invoke a real channel.
