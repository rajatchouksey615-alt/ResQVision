# Authorization Contract

Authorization is enforced by the backend on every request. Client visibility is not a security decision. Human and machine actors are created only from authenticated request principals; a serializer or caller cannot provide a domain actor.

## Human Scope

- The authenticated database user must be active. The profile endpoint reads and updates only that account; PATCH permits only `first_name` and `last_name`.
- `ADMIN`, `POLICE`, and `HOSPITAL` group names are read dynamically. A group label is not equivalent to `is_superuser` or `is_staff` and does not bypass object scope.
- Organization-scoped access requires an active membership, active organization, and membership group matching the organization kind.
- Incident summaries and assignments are scoped to the user's active organization assignment. Cancelled/replaced assignments do not provide ongoing incident access. A detail outside scope returns 404.
- Assignment acknowledgement, start, activity, inability-to-respond, and completion commands use the existing response services, which recheck membership and enforce state transitions. Activity kinds must match the target organization kind.
- Notifications are selected by recipient user. Mark-read calls the existing notification service; another user's notification is reported as 404.
- Collection authorization is applied before pagination. Only explicit `status` filters are accepted for incidents and notifications.

## Fail-Closed Operations

These operations return a stable 503 policy/storage error and do not query the supplied object to determine whether it exists:

- Candidate queue/detail, event association, and review: reviewer authority is unresolved under OAD-012.
- Video source listing/detail/registration: source visibility and registration authority are unresolved under OAD-019.
- Incident resolve and close: authority is unresolved under OAD-012 and OAD-018.
- Assignment cancellation and reassignment: authority is unresolved under OAD-013/OAD-018.
- Evidence metadata listing/detail: role-specific evidence fields and access policy remain unresolved. Upload-session operations are unavailable because no storage provider/verifier is configured.
- Location provenance reads: precision and role scope remain unresolved under OAD-020.
- Assignment creation: no HTTP route is exposed because creation authority remains unresolved under OAD-013.
- Audit event listing, user registration, user/role administration, and emergency dispatch have no public API route.

## Machine Scope

AI_SERVICE is not a Django user or group. It cannot call human account operations, candidate or incident decisions, assignment/response commands, notifications, or general evidence reads. Machine identity is obtained only from a configured dedicated authenticator. The authenticator is currently unconfigured under OAD-017, so detection submission fails closed.

No policy grants ADMIN blanket evidence, audit, incident, source, or assignment access. No candidate, incident, evidence, or location policy is inferred from group membership alone.
