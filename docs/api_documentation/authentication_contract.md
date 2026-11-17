# Human and Machine Authentication

## Human JWT

Human authentication uses the existing `accounts.User` model, normalized email, Django password hashing, and database-backed SimpleJWT authentication. Public registration is not implemented. Browser session authentication is not enabled for API views; Django Admin keeps its normal session flow.

| Operation | Method and path | Request | Success |
|---|---|---|---|
| Obtain token pair | `POST /api/v1/auth/token/` | `{"email":"user@example.test","password":"..."}` | `{"access":"...","refresh":"..."}` |
| Rotate refresh token | `POST /api/v1/auth/token/refresh/` | `{"refresh":"..."}` | New `access` and `refresh` tokens |
| Logout current refresh session | `POST /api/v1/auth/logout/` | Bearer access token and `{"refresh":"..."}` | `204 No Content` |
| Read current identity | `GET /api/v1/auth/me/` | Bearer access token | Safe profile, current group labels, active own memberships |
| Change own password | `POST /api/v1/auth/password/change/` | `{"current_password":"...","new_password":"..."}` | `204 No Content` |

Access tokens last 5 minutes; refresh tokens last 1 day. Refresh tokens rotate on use, and the previous refresh token is blacklisted. Logout requires a valid access token and a refresh token belonging to that same user. Repeating logout for an already blacklisted refresh token is safe. The API does not claim refresh-token-family compromise detection.

Logout blacklists the supplied refresh token. An already-issued access token remains usable until its 5-minute expiry; password changes revoke access tokens immediately through the password-revocation check.

The allowed JWT algorithm is HS256. The stable user UUID, token type, JTI, issue/expiry timestamps, and SimpleJWT password-revocation marker are used. Organization membership and role data are not stored in token claims; authorization reads current database state.

`JWT_SIGNING_KEY` must be a unique value of at least 32 characters and must differ from `DJANGO_SECRET_KEY`. Development and test settings provide local-only fallback values. Shared environments must configure their own secret, use HTTPS, and trust forwarded HTTPS headers only from a secured reverse proxy.

Password change checks the current password and Django password validators. The supported SimpleJWT password-revocation mechanism is enabled for access tokens, and refresh validation checks the same marker. A password change immediately invalidates prior tokens; the user signs in again. `UPDATE_LAST_LOGIN` remains disabled.

Login is limited to 5 attempts/minute per client IP and refresh to 20/minute by DRF. Sensitive commands use 30/minute. These are in-process limits; production still requires reverse-proxy rate limiting.

## AI_SERVICE Boundary

`POST /api/v1/ai/detection-events/` has a dedicated `AIServiceAuthentication` interface. It does not use the human JWT authenticator and never accepts a `service_ref` from the body or headers as identity proof. The default configuration is unset and responds with `503 machine_authentication_unavailable`.

A deliberately test-only authenticator can be injected in test settings. It is disabled when `TESTING` is false. OAD-017 is unresolved, so no production machine credential, shared token, OAuth client, signing key, or mTLS identity is configured. Even with a future authenticator, the route must preserve the domain service's source-authorization and idempotency checks.
