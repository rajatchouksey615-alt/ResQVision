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
| GET | `/incidents/` | Human bearer token | Assignment-scoped incident summaries; optional allow-listed `status` filter |
| GET | `/incidents/{incident_id}/` | Human bearer token | Assignment-scoped summary; out-of-scope is 404 |
| POST | `/incidents/{incident_id}/resolve/` | Human bearer token | 503 until resolution authority is approved |
| POST | `/incidents/{incident_id}/close/` | Human bearer token | 503 until closure authority is approved |
| GET | `/incidents/{incident_id}/assignments/` | Human bearer token | Only assignments visible to the caller’s active organization membership |
| GET | `/assignments/{assignment_id}/` | Human bearer token | Own organization assignment; out-of-scope is 404 |
| POST | `/assignments/{assignment_id}/acknowledge/` | Assigned organization | Acknowledges with `{"command_id":"<uuid>"}` |
| POST | `/assignments/{assignment_id}/start/` | Assigned organization | Starts simulated response; body has `command_id` and optional `details` |
| POST | `/assignments/{assignment_id}/activities/` | Assigned organization | Body has `command_id`, `activity_kind`, optional `details` |
| POST | `/assignments/{assignment_id}/unable-to-respond/` | Assigned organization | Body has `command_id` and required `reason` |
| POST | `/assignments/{assignment_id}/complete/` | Assigned organization | Body has `command_id` and required `details` |
| POST | `/assignments/{assignment_id}/cancel/` | Human bearer token | 503 until cancellation authority is approved |
| POST | `/assignments/{assignment_id}/reassign/` | Human bearer token | 503 until reassignment authority is approved |

Writes call `apps.responses.services.assignments`. Command responses contain `data` and `replayed`. Each agency assignment and history remains independent; a command does not send a real notification or dispatch a responder.

## Detection, Candidates, Sources, Evidence, Locations, Notifications

| Method | Path | Access | Current behavior |
|---|---|---|---|
| POST | `/ai/detection-events/` | Dedicated AI_SERVICE only | 503 while machine auth is unconfigured under OAD-017; never accepts human JWT as machine identity |
| GET | `/candidates/` | Human | 503 until reviewer/queue authority is approved |
| GET | `/candidates/{candidate_id}/` | Human | 503 until candidate read authority is approved |
| POST | `/candidates/{candidate_id}/associate-events/` | Human | 503 until association authority is approved |
| POST | `/candidates/{candidate_id}/review/` | Human | 503 until reviewer authority is approved |
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

Domain command writes require a UUID `command_id`. Retry with the same command ID and same intent after an uncertain response. A reused command ID with different intent returns `409 idempotency_conflict`. Passwords, refresh tokens, and access tokens are never sent in URL parameters.

The OpenAPI schema at `/schema/` is generated from the implementation and is also committed as [`openapi.yaml`](openapi.yaml). See the [authentication](authentication_contract.md), [authorization](authorization_contract.md), and [error](error_handling.md) contracts for detailed rules.
