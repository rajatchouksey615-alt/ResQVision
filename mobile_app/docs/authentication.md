# Authentication Contract and Session Lifecycle

Phase 5B integrates the Flutter client with the Django human JWT API. Django remains the source of identity, roles, organization membership, and authorization decisions.

## Audited backend contract

| Operation | Request | Success | Behavior |
| --- | --- | --- | --- |
| Login | `POST /api/v1/auth/token/` with `email`, `password` | `200` with `access`, `refresh` | Email is trimmed and lowercased by the backend. Incorrect and inactive-account credentials share a generic `401`. Login is throttled at 5 requests per minute. |
| Refresh | `POST /api/v1/auth/token/refresh/` with `refresh` | `200` with replacement `access`, `refresh` | Refresh rotation is enabled; the previous refresh token is blacklisted. Refresh is throttled at 20 requests per minute. Expired, revoked, reused, and password-stale tokens return `401`. |
| Current user | `GET /api/v1/auth/me/` with `Authorization: Bearer <access>` | `200` with user identity, `roles`, and `memberships` | Roles are read from approved Django groups. Memberships are filtered to active memberships and include organization identifiers, names, kinds, role, and status. JWT claims do not contain roles. |
| Logout | `POST /api/v1/auth/logout/` with Bearer access and `{ "refresh": "…" }` | `204` | The authenticated user can blacklist only their own refresh token. Repeated logout is safe. An expired access token cannot authenticate the revocation request. |

API errors use a stable envelope containing `code` and `detail`, with optional `errors` and `request_id`. Login, refresh, and logout preserve the backend's `401`, `403`, and `429` responses; the mobile UI maps them to safe messages and does not display raw server details.

Token lifetimes are five minutes for access credentials and one day for refresh credentials. The backend checks the user's active state and password-revocation claim during refresh. A password change invalidates earlier tokens.

## Mobile credential handling

- `FlutterTokenStorage` uses `flutter_secure_storage` and separate access and refresh keys. Android uses the plugin's encrypted platform storage; Windows uses the plugin's Windows backend.
- Android backup is disabled so an encrypted credential is not restored without its platform key. Cleartext HTTP remains limited to the existing debug/profile manifests; production `API_BASE_URL` requires HTTPS.
- Passwords are sent only in the login request and are never written to token storage. Storage failures are reported explicitly; there is no plaintext fallback.
- Pair replacement writes the rotated refresh token first, then access. If either write fails, both local keys are cleared where the platform allows it, and the app does not claim a persistent sign-in.

## Session and request flow

1. Startup reads the secure token pair and calls `/auth/me/`. A `401` triggers one refresh attempt and then one profile retry. The app exposes a protected workspace only after the backend profile has been parsed successfully.
2. A temporary network or server failure leaves saved credentials intact and presents a retry action. A confirmed invalid refresh clears the pair and returns to login.
3. Authenticated requests attach Bearer access credentials. Concurrent `401` responses share one refresh future; the replacement pair is stored before waiting requests continue. A stale access response reuses the newer access credential instead of rotating twice.
4. Only `GET`, `HEAD`, and `OPTIONS` requests are replayed once after refresh. Unsafe requests are not replayed. `403` and `429` do not start a refresh.
5. Logout invalidates the in-memory session immediately, clears local credentials, prevents older asynchronous work from restoring the session, and submits the backend logout request with the captured access/refresh pair. If the server cannot confirm revocation, the login screen reports that status while keeping the user signed out locally.

The role-aware UI uses the roles and active memberships from `/auth/me/` to render placeholder workspaces. Those client-side entry points do not authorize API operations; every protected operation remains subject to Django permissions.

