# Endpoint Reference

Base prefix: `/api/v1/`. JSON timestamps are timezone-aware ISO 8601. Protected calls use `Authorization: Bearer <access_token>`. All responses include `X-Request-ID`.

## Authentication and Accounts

| Method | Path | Access | Current behavior |
|---|---|---|---|
| POST | `/auth/token/` | Public, throttled | Email/password login; returns 5-minute access and 1-day refresh token |
| POST | `/auth/token/refresh/` | Refresh token, throttled | Rotates refresh token and blacklists the prior token |
| POST | `/auth/logout/` | Human bearer token | Blacklists only the caller's refresh session; repeat is safe |
| GET | `/auth/me/` | Human bearer token | Own safe profile, current group labels, active memberships |
| POST | `/auth/password/change/` | Human bearer token | Changes own password and revokes prior tokens |
| GET | `/accounts/me/` | Human bearer token | Own email and names |
| PATCH | `/accounts/me/` | Human bearer token | Updates only `first_name` and `last_name` |
| GET | `/organizations/me/` | Human bearer token | Active memberships belonging to the caller |
| GET | `/organizations/{organization_id}/memberships/` | Human bearer token | Caller’s own membership in that organization; never lists other members |

## Incidents and Response Assignments

| Method | Path | Access | Current behavior |
|---|---|---|---|
| GET | `/incidents/` | Human bearer token | Assignment-scoped incident summaries; optional allow-listed `status` filter. Hospital users see incidents assigned to their active Hospital memberships |
| GET | `/incidents/{incident_id}/` | Human bearer token | Minimum assignment-scoped summary; out-of-scope is 404 |
| POST | `/incidents/{incident_id}/resolve/` | Human bearer token | 503 until resolution authority is approved |
| POST | `/incidents/{incident_id}/close/` | Human bearer token | 503 until closure authority is approved |
| GET | `/incidents/{incident_id}/assignments/` | Human bearer token | Only assignments visible to the caller’s active organization membership; a parent incident outside the caller’s current scope returns 404 |
| GET | `/assignments/{assignment_id}/` | Human bearer token | Own organization assignment; current matching membership is checked; out-of-scope is 404 |
| POST | `/assignments/{assignment_id}/acknowledge/` | Assigned organization | Police-target commands use the existing service; Hospital-target commands return 503 `policy_unavailable` pending OAD-018 |
| POST | `/assignments/{assignment_id}/start/` | Assigned organization | Police-target commands use the existing service; Hospital-target commands return 503 `policy_unavailable` pending OAD-018 |
| POST | `/assignments/{assignment_id}/activities/` | Assigned organization | Police-target commands use the existing service; Hospital-target commands return 503 `policy_unavailable` pending OAD-018 |
| POST | `/assignments/{assignment_id}/unable-to-respond/` | Assigned organization | Police-target commands use the existing service; Hospital-target commands return 503 `policy_unavailable` pending OAD-018 |
| POST | `/assignments/{assignment_id}/complete/` | Assigned organization | Police-target commands use the existing service; Hospital-target commands return 503 `policy_unavailable` pending OAD-018 |
| POST | `/assignments/{assignment_id}/cancel/` | Human bearer token | 503 until cancellation authority is approved |
| POST | `/assignments/{assignment_id}/reassign/` | Human bearer token | 503 until reassignment authority is approved |

Writes call `apps.responses.services.assignments`. Command responses contain `data` and `replayed`. Each agency assignment and history remains independent; a command does not send a real notification or dispatch a responder. The Hospital Flutter workspace is read-only: it lists the caller’s assigned incidents and shows the minimum incident summary and Hospital assignment status. Hospital writes remain unavailable until OAD-018 approves the lifecycle, actors, and transitions. Evidence and location remain unavailable.

No response-assignment creation endpoint is exposed. `create_assignment` requires an injected authorization policy and the production default denies it; OAD-013 has not approved who selects/designates the Hospital or who may create/reassign the assignment. The API must stay fail-closed until that policy is recorded. Hospital response detail beyond the existing assignment summary, including a distinct simulated dispatch decision/status model, is also unresolved under OAD-018.

## Detection, Candidates, Sources, Evidence, Locations, Notifications

| Method | Path | Access | Current behavior |
|---|---|---|---|
| POST | `/ai/detection-events/` | Dedicated AI_SERVICE only | v1 contract; 503 while machine auth is unconfigured under OAD-017; source must be authorized and available; intake stores an event only |
| GET | `/candidates/` | Active assigned Police reviewer | Lists only candidates assigned to the caller in their active Police organization |
| GET | `/candidates/{candidate_id}/` | Active assigned Police reviewer | Assigned candidate detail; out-of-scope is 404 |
| POST | `/candidates/{candidate_id}/assignment/` | ADMIN-group user with active membership in the candidate Police organization | Assigns one active same-organization Police reviewer; body has `reviewer_id` and `command_id` |
| POST | `/candidates/{candidate_id}/review/` | Specifically assigned reviewer with active Police membership | Starts review; body has `command_id`; only `RECEIVED` can enter `UNDER_REVIEW` |
| POST | `/candidates/{candidate_id}/verify/` | Specifically assigned reviewer with active Police membership | Records `VERIFIED` and atomically creates one `OPEN` incident; body has `command_id` and optional `rationale` |
| POST | `/candidates/{candidate_id}/reject/` | Specifically assigned reviewer with active Police membership | Records `REJECTED` without creating an incident; body has `command_id` and required nonblank `rationale` |
| POST | `/candidates/{candidate_id}/associate-events/` | Human | 503 until association authority is approved |
| GET | `/video-sources/` | Human | 503 until source read scope is approved |
| POST | `/video-sources/` | Human | 503 until source registration authority is approved |
| GET | `/video-sources/{source_id}/` | Human | 503 until source read scope is approved |
| GET | `/evidence/` | Human | 503 until evidence metadata policy is approved |
| GET | `/evidence/{evidence_id}/` | Human | 503 until evidence metadata policy is approved |
| POST | `/evidence/upload-sessions/` | Human | 503 `evidence_storage_unavailable`; no provider is configured |
| POST | `/evidence/upload-sessions/{session_id}/complete/` | Human | 503 `evidence_storage_unavailable`; no trusted verifier exists |
| GET | `/incidents/{incident_id}/locations/` | Human | 503 until location precision/scope policy is approved |
| GET | `/notifications/` | Human bearer token | Recipient-owned notifications; optional allow-listed `status` filter |
| POST | `/notifications/{notification_id}/read/` | Human bearer token | Marks own delivered-simulated notification read through the domain service |

## Collection and Command Rules

Collections use `limit` and `offset`; default limit is 25 and maximum is 100. `status` is the only currently exposed collection filter. Do not send arbitrary model field names or ordering clauses.

Domain command writes require a UUID `command_id`. Retry with the same command ID and same intent after an uncertain response. A reused command ID with different intent returns `409 idempotency_conflict`. Candidate reviewer assignment is one-time; another assignment request returns `409 resource_conflict`, with no reassignment or unassignment route. Passwords, refresh tokens, and access tokens are never sent in URL parameters.

Candidate review and final decisions recheck the assigned reviewer, active account, active Police organization, and active Police membership on each request. Out-of-scope candidate IDs return 404. A reviewer can record only one final decision; a decision command replay with the same command ID and intent returns its prior result. `FURTHER_REVIEW` is not an available operation.

The OpenAPI schema at `/schema/` is generated from the implementation and is also committed as [`openapi.yaml`](openapi.yaml). See the [authentication](authentication_contract.md), [authorization](authorization_contract.md), and [error](error_handling.md) contracts for detailed rules.
