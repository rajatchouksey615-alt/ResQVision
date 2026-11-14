# User Role Workflows

**Status:** Proposed workflows for team review; exact scope and verification authority require approval. See the [role-permission matrix](../requirements/role_permission_matrix.md).

## Common Authentication and Access

1. User submits credentials through the mobile client.
2. Backend authenticates and returns the approved session/token behavior (lifecycle TBD).
3. Backend determines role and resource scope for each request; client navigation is not an access control.
4. User sees only authorized incidents and actions. Denied requests do not disclose protected object details.
5. Logout clears the client session; token revocation and local cache behavior are TBD.

## ADMIN Workflow

~~~mermaid
flowchart TD
    A[Authenticate] --> B{Admin permission valid?}
    B -- No --> X[Access denied and safe error]
    B -- Yes --> C[View admin dashboard]
    C --> D{Choose action}
    D --> E[Manage users and roles]
    D --> F[Review incident queue]
    F --> G[Review evidence and uncertainty]
    G --> H{Verification permission approved?}
    H -- No --> I[View only or refer for review]
    H -- Yes --> J[Record verified/rejected decision]
    J --> K[Assign only verified incident]
    C --> L[Inspect permitted reports/audit]
    E --> M[Backend validates and audits]
    J --> M
    K --> M
    L --> M
~~~

Admin account and role administration is required. Admin candidate verification and assignment are proposed permissions; the team must approve reviewer/assignment authority and evidence scope.

## POLICE Workflow

1. Authenticate and load only incidents in approved scope.
2. Open an assigned incident and review permitted summary/evidence.
3. Acknowledge the simulated assignment.
4. Record permitted response progress and, if authorized, resolution.
5. Review scoped incident history and log out.

Out-of-scope reads, administrative changes, and invalid/stale transitions are denied. Police users do not trigger real dispatch in this prototype.

## HOSPITAL Workflow

1. Authenticate and load only assigned incidents in approved scope.
2. Review the minimum incident information needed for simulated readiness.
3. Acknowledge the assignment and record readiness/status updates.
4. Review permitted history and log out.

Hospital users do not administer users or access unrelated evidence. Permitted details, readiness states, and incident scope remain subject to privacy and team review.

## AI Service Workflow

The AI service uses a separate machine identity; it is not an Admin/Police/Hospital user. It may submit candidate evidence and receive an intake outcome. It cannot browse user data, verify or reject authoritatively, assign responders, update response state, or contact emergency services.

## Failure and Exception Paths

- Expired/invalid credentials: deny protected access and show a safe retry path.
- Role/scope mismatch: deny action and do not reveal whether another incident exists.
- Evidence unavailable: preserve incident visibility and mark the evidence unavailable.
- Backend/network failure: show retryable status without claiming a state change succeeded.
- Stale or invalid state: reject the transition and refresh current state.
- Simulated notification failure: record/report the simulation outcome; never invoke a real channel.
