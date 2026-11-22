# Incident Management Engineering Report

**Status: PARTIALLY_COMPLETE**  
**Repository:** `main`, baseline commit `c462063` (`feat(dashboard): implement role-based workspaces and integration tests`)  
**Scope:** Flutter incident read experience using existing Django APIs. No backend policy, schema, or migration changes.

## 1. Executive Summary

Implemented a paginated, role-aware incident list and a read-only incident detail screen in the established Flutter shell. The list uses the backend's supported status filter and continuation metadata. The detail screen shows the incident summary and only assignments matching the selected workspace's active memberships. Candidate review, verification, evidence, location, incident resolution, and closure remain unavailable because their API policies are explicitly blocked or unresolved.

## 2. Repository Audit

- The working tree was clean on `main` at `c462063` before changes; no dashboard-integration edits were pending.
- Existing Flutter authentication, token refresh coordination, membership model, dashboard controller, and role shell were retained.
- Django APIs are centralized under `backend/api/v1/`; incident behavior is in `apps.incidents`, assignment behavior in `apps.responses`, and read scoping in `api.v1.selectors` and domain policies.
- Requirements, role matrix, incident workflow, ERD, and open architecture decisions were inspected. OAD-012 (candidate reviewer authority) remains TBD; OAD-020 (location policy) remains pending.

## 3. Domain Lifecycle Map

| Record | Actual lifecycle | Boundary |
|---|---|---|
| `DetectionEvent` | Accepted machine observation with source and event provenance | It is never an incident. |
| `AccidentCandidate` | `RECEIVED` → `UNDER_REVIEW` → `VERIFIED` or `REJECTED` | Candidate association and review are backend service operations. |
| `AccidentIncident` | Created as `OPEN` only after candidate verification; may become `RESPONSE_ACTIVE`, `RESOLVED`, then `CLOSED` | Verification creates the candidate review, state change, incident, and initial history atomically; command IDs support replay checks. |
| `ResponseAssignment` | Independent Police or Hospital target lifecycle | One assignment does not acknowledge or complete another agency's assignment. |

`resolve_incident` requires every assignment to be terminal and an approved policy; `close_incident` requires `RESOLVED` and an approved policy. Reopen is not an implemented API command.

## 4. API Contract Map

All listed human routes require a valid human JWT. Collections use DRF `LimitOffsetPagination` (`count`, `next`, `previous`, `results`; default 25, maximum 100). The mobile client requests 10 incidents and 100 assignments per page.

| Endpoint | Contract and scope | Service/policy and errors |
|---|---|---|
| `GET /api/v1/incidents/` | Optional `status` only, plus `limit` and `offset`. Each result is `{id, status, created_at, updated_at}`. Search and organization query parameters are not implemented. | `visible_incident_queryset` filters by active target organization and active matching membership before pagination. Invalid status is 400. |
| `GET /api/v1/incidents/{incident_id}/` | Same incident summary shape. | `get_incident` with `AssignedIncidentReadPolicy`; an out-of-scope or missing incident is concealed as 404. |
| `GET /api/v1/incidents/{incident_id}/assignments/` | Paginated assignment summaries: `{id, incident_id, target_organization_id, target_organization_kind, status, created_at, updated_at}`. | `visible_assignment_queryset`; active assignment target and membership are required. Out-of-scope rows are omitted. |
| `GET /api/v1/assignments/{assignment_id}/` | One assignment summary. | Same assignment queryset; missing or out-of-scope is 404. |
| `GET /api/v1/candidates/`, `GET /api/v1/candidates/{id}/`, `POST /api/v1/candidates/{id}/review/` | Routes exist but are deliberately disabled. | `PolicyNotConfigured`; returns 503 `policy_unavailable` without revealing candidate existence. |
| `GET /api/v1/evidence/`, `GET /api/v1/evidence/{id}/` | Metadata/read routes exist but are disabled; there is no usable media retrieval contract. | `PolicyNotConfigured`; returns 503. Upload routes also do not provide a complete usable mobile upload/retrieval workflow. |
| `GET /api/v1/incidents/{id}/locations/` | Route exists; no location representation is currently available to the mobile client. | `PolicyNotConfigured`; returns 503. No location is embedded in incident summaries. |
| `POST /api/v1/incidents/{id}/resolve/`, `POST /api/v1/incidents/{id}/close/` | Routes exist with no enabled request contract. | `PolicyNotConfigured`; returns 503. |

Assignment acknowledge/start/activity/unable-to-respond/complete commands exist and use command IDs, but assignment lifecycle UI is excluded from this scope. Cancel and reassign are policy-blocked.

## 5. Authorization Matrix

| Workspace | API data shown | Client filtering |
|---|---|---|
| ADMIN | Only incident records reachable through the user's active Police/Hospital memberships and assignments; Admin is not global. | Matches returned assignments to eligible active memberships. |
| POLICE | Only Police-target assignments with an active Police membership. | Filters each bounded incident page and detail to the selected Police role and organization. |
| HOSPITAL | Only Hospital-target assignments with an active Hospital membership. | Filters each bounded incident page and detail to the selected Hospital role and organization. |
| AI_SERVICE | No mobile workspace. | Machine identity remains separate from human roles. |

Backend authorization remains authoritative. The local organization selector is only a display filter and is never sent as an authorization claim. HTTP 401 is handled through the existing session client; 403 and concealed 404 are mapped distinctly. No frontend role check can grant an API operation.

## 6. Incident Listing Implementation

Added a typed incident repository and list controller. The list supports the backend `status` filter, bounded pagination, continuation offsets parsed from the backend `next` link, loading/empty/error/retry states, stale-response protection, and assignment-scope filtering. Search is identified as unavailable because the API has no search parameter. Backend `count` is labeled as the combined authorized membership scope, not as a role-specific total.

## 7. Incident Detail Implementation

Added a detail screen for the actual incident summary and permitted assignment summaries. It presents status, identifier, and timestamps. Assignment requests remain bounded and disclose a partial result when the backend returns a continuation link. The page is read-only.

## 8. Candidate Review Implementation

The incident-management screen explains that candidate queue, detail, and review APIs are policy-blocked (503). No candidate records or review actions are fabricated or submitted.

## 9. Candidate Review Implementation Status

**Blocked.** The domain service `verify_candidate` is transactional and idempotent, but the API route is disabled and OAD-012 leaves reviewer authority unresolved. The requirements matrix only proposes designated Admin review and explicitly leaves the decision TBD. No verification control is exposed and no backend policy was changed.

## 10. Incident Lifecycle Operations

**Read-only.** The API's resolve and close endpoints return 503 while their policies are unresolved. The mobile app does not submit lifecycle commands or optimistically change status. Assignment commands remain outside the requested UI scope.

## 11. Evidence Implementation

**Unavailable by backend policy.** Evidence list/detail and authorization-controlled media retrieval are not usable. The detail screen reports this state and exposes no object keys, storage paths, credentials, or private links. No upload workflow was added.

## 12. Location Provenance Implementation

**Unavailable by backend policy.** The location endpoint returns 503 and incident summaries contain no location. The detail screen explains that coordinates and provenance cannot be displayed. No camera coordinates are mislabeled as accident coordinates, and no map provider was added.

## 13. Files Created

- `mobile_app/lib/features/incidents/data/incident_repository.dart`
- `mobile_app/lib/features/incidents/application/incident_list_controller.dart`
- `mobile_app/lib/features/incidents/presentation/incident_management_screen.dart`
- `mobile_app/lib/features/incidents/presentation/incident_detail_screen.dart`
- `mobile_app/test/unit/incident_repository_test.dart`
- `mobile_app/test/widget/incident_management_widget_test.dart`
- `docs/incident_management/incident_management_report.md`

## 14. Files Modified

- Flutter app/bootstrap/session/role landing and dashboard shell to inject and expose incident management.
- Test support and dashboard/authentication/navigation widget tests to cover app wiring.

## 15. Backend Changes

None. Existing domain services, API permissions, and routes were not changed.

## 16. Migration Status

No migrations created or modified.

## 17. Unit Test Results

Incident repository tests cover typed parsing, status query construction, continuation metadata, active membership checks, role/organization assignment filtering, safe 403 mapping, and policy-blocked 503 messaging. The full Flutter suite passed.

## 18. Widget Test Results

Widget tests cover incident listing, dashboard navigation, detail/assignment rendering, unavailable evidence and location, blocked candidate review, status selection, load-more interaction, and read-only status.

## 19. Live Integration Test Results

Live API tests did not run. The full Flutter suite reported 7 integration tests skipped because the API/account environment variables were not configured. The repository runner was attempted with its required local-fixture opt-in; it stopped before starting Django because an existing managed `.test` fixture account has a different password from the process-only credential. Password rotation was not requested and was not performed. Fixture setup is transaction-wrapped, so the failed attempt rolled back; no local server was started.

## 20. Backend PostgreSQL Test Results

- `python manage.py check`: passed, no issues.
- `python -m pytest -q`: **89 passed** using the repository's PostgreSQL test settings.
- The API regression tests exercise assignment scoping, concealed 404 responses, policy-blocked 503 responses, pagination, and state-transition authorization.

## 21. Flutter Analyzer and Build Results

- `flutter pub get --offline`: passed.
- Dart format check: passed, 67 files checked with no changes required.
- `flutter analyze --no-pub`: passed, no issues.
- `flutter test --no-pub`: **71 passed, 7 skipped** (all skips were live integration tests without configured accounts/server).
- `flutter build apk --debug --no-pub`: passed.

## 22. Security Review

- Reused `AuthenticatedApiClient`; no duplicate JWT or token-refresh logic was added.
- Kept backend scoping authoritative and filtered visible assignments against current profile memberships for workspace presentation.
- Preserved the distinction between detection event, candidate, and authoritative incident.
- Did not enable candidate verification, resolution, closure, evidence access, or location access.
- No emergency dispatch, notification delivery, or assignment lifecycle was added.
- No secrets, test passwords, or private media references were added to source or logs.

## 23. Git Diff Summary

Changes are limited to Flutter incident UI/data/state wiring, Flutter tests, and this report. No commit or push was made. A final `git diff --check` and status review are recorded after report creation.

## 24. Known Limitations

- Candidate queue/detail/review/verification, evidence, and location require approved backend policies and usable endpoint contracts.
- Resolve/close require approved backend policies.
- Search and organization/date query filters are not supported by the incident API.
- Incident count is for the backend's combined authorized membership scope; role/organization filtering occurs on bounded assignment pages in the client.
- Live Flutter/PostgreSQL integration coverage remains unverified because the existing managed `.test` credential is unavailable without rotating it.

## 25. Candidate Verification Readiness

**Incident management is not ready to report as complete.** The incident list/detail read experience and isolated regression coverage are implemented and validated. Work remains partial until candidate reviewer authority (OAD-012), evidence access scope, location policy, and incident resolve/close authority are approved and enabled, and the live role-specific integration run can use the existing dedicated test credentials.
