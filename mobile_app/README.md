# ResQVision Mobile

**Status:** Phase 5B human authentication and secure session management are implemented on the Phase 5A foundation. Android is the primary target and Windows is supported for development. This project does not create a Web target.

## Foundation

- Feature-first code under `lib/app`, `lib/core`, and `lib/features`.
- Central bootstrap, light/dark Material 3 themes, named routes, and safe unknown-route handling.
- Required compile-time API configuration with URL validation.
- A shared HTTP client with timeouts, stable transport errors, and explicit JSON content lengths for Django compatibility.
- Backend-integrated email login, secure Android/Windows token storage, refresh rotation, and session restoration.
- Authenticated requests with single-flight refresh, a single retry for safe reads, and backend profile-driven workspace placeholders.
- Shared loading, empty, and error states; buttons, a text-field foundation, cards, headings, and a confirmation dialog.
- Structured development logging that records event identifiers and exception types without exception messages or stack traces.
- Deterministic unit and widget tests under `test/unit` and `test/widget`.

Session state uses Flutter's `ChangeNotifier`; no general state-management dependency is selected. Navigation uses Flutter's built-in `Navigator`. The HTTP transport uses Dart's built-in `dart:io` library; a Web target would need a browser-compatible transport before it is enabled.

## Configure the API URL

Set `API_BASE_URL` at build time. The value must be an absolute HTTP or HTTPS URL without credentials, query parameters, or a fragment. The initial value has no developer-specific default; the app displays a setup state when it is missing or invalid. `APP_ENV` is optional and defaults to `development`; production configuration requires HTTPS.

The backend mounts its API at `/api/v1/`. Django's development server uses port `8000` by default; the repository does not configure a separate API server port. Adjust the port in these examples if the backend is started on another port.

```powershell
# Android emulator
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1/

# Windows desktop
flutter run -d windows --dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1/

# Physical Android device: replace the host with an address reachable by the device
flutter run --dart-define=API_BASE_URL=http://<development-machine-ip>:8000/api/v1/
```

Compile-time values are bundled into the app. Do not put passwords, tokens, database credentials, or AI service credentials in Dart defines. Root `.env` settings belong to the backend and are not read by Flutter. Android cleartext traffic is enabled only for debug and profile builds to support local HTTP development; production configuration must use HTTPS.

## Run checks

Run these commands from `mobile_app/`:

```powershell
flutter pub get
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test
```

`test/integration/live_backend_auth_test.dart` exercises login, profile retrieval, refresh rotation, restoration, logout, and revocation against a live Django server when `RESQVISION_TEST_API_BASE_URL`, `RESQVISION_TEST_EMAIL`, and `RESQVISION_TEST_PASSWORD` point to an isolated local test account. `test/integration/live_dashboard_test.dart` also accepts the generic account for a single-account role check. Dedicated workspace tests use `RESQVISION_TEST_ADMIN_EMAIL` / `RESQVISION_TEST_ADMIN_PASSWORD`, `RESQVISION_TEST_POLICE_EMAIL` / `RESQVISION_TEST_POLICE_PASSWORD`, and `RESQVISION_TEST_HOSPITAL_EMAIL` / `RESQVISION_TEST_HOSPITAL_PASSWORD`; each email must be distinct and use a reserved `.test` domain. The live dashboard tests check the roles and active memberships returned by Django, and test Police↔Hospital assignment isolation and cross-account logout ownership. The Admin fixture has no active operational membership; its suspended Police membership verifies that the backend does not grant data access based on inactive scope.

### Local live integration fixture

The live-test setup command is deliberately restricted to `DEBUG=True`, PostgreSQL, loopback database connections, and the connected database named exactly `resqvision_dev`. It also requires explicit process opt-in with `RESQVISION_LOCAL_TEST_DATA_OPT_IN=1`. From the repository root, run:

```powershell
$env:RESQVISION_LOCAL_TEST_DATA_OPT_IN = '1'
$env:RESQVISION_TEST_API_BASE_URL = 'http://127.0.0.1:8001/api/v1/'
# Optional: provide dedicated local accounts and replace password placeholders.
$env:RESQVISION_TEST_EMAIL = 'phase5c.auth@resqvision.test'
$env:RESQVISION_TEST_PASSWORD = '<local-generic-test-password>'
$env:RESQVISION_TEST_ADMIN_EMAIL = 'phase5c.admin@resqvision.test'
$env:RESQVISION_TEST_ADMIN_PASSWORD = '<local-admin-test-password>'
$env:RESQVISION_TEST_POLICE_EMAIL = 'phase5c.police@resqvision.test'
$env:RESQVISION_TEST_POLICE_PASSWORD = '<local-police-test-password>'
$env:RESQVISION_TEST_HOSPITAL_EMAIL = 'phase5c.hospital@resqvision.test'
$env:RESQVISION_TEST_HOSPITAL_PASSWORD = '<local-hospital-test-password>'
.\mobile_app\scripts\run_local_live_integration.ps1
```

The runner uses the existing test variables above. If an account email and password pair is both absent, it uses a reserved local `.test` email and creates a random password in the current PowerShell process only. If only one value in a pair is supplied, it fails rather than substituting another identity. Supply both values to reuse a managed account. To explicitly replace passwords only for accounts already marked by the local fixture, pass `-RotateManagedTestPasswords`; an existing unmarked account is always rejected. The runner starts Django on loopback at the configured port, verifies the anonymous incident endpoint returns `401`, runs the live role and cross-account checks, waits for the documented login throttle window, then runs the Phase 5B lifecycle test. It refuses a nonlocal API URL or a port already owned by another process. It does not print, save, or report passwords or tokens.

The command `python manage.py setup_local_dashboard_test_data` creates or reuses four managed users (ADMIN, POLICE, HOSPITAL, and a role-free generic authentication identity), one test-only Police organization, one test-only Hospital organization, one source-owner organization, active Police/Hospital memberships, and one suspended Police membership for the Admin fixture. It then creates one controlled-file video source and six detection events; each event goes through candidate review/verification to an OPEN incident with independent PENDING Police and Hospital assignments. Six incidents make the live `limit=5` response return real backend continuation metadata. Django also records the associated source, review, and assignment audit/history rows. The ADMIN has no active operational membership, staff or superuser privileges, and the suspended membership verifies that inactive scope does not reveal incident data. The setup does not create notifications, send messages, contact outside services, dispatch emergency responders, or delete records. Records remain in `resqvision_dev`; no automatic cleanup is provided.

The local-only fixture command uses a narrow policy object only while invoking existing domain services from that management command. No API authorization policy or production authentication behavior is changed. Live tests require the local API base URL and each intended account's email/password variables; without them, they skip with a specific reason. Never use a production or personal account, commit credentials, or put passwords in `.env.example` or test reports. The generic Phase 5B lifecycle test must run separately from the three role accounts to stay within Django's login throttle.

## Scope boundaries

This phase implements human login and session handling only. Incident or assignment workflows, push notifications, maps, AI integration, emergency dispatch, and production deployment remain out of scope. The backend remains authoritative for identity and authorization. No real emergency service, police, hospital, or ambulance dispatch is connected.

See [mobile architecture](docs/architecture.md), the [authentication contract and lifecycle](docs/authentication.md), the [project testing strategy](../docs/testing/testing_strategy.md), and the [contribution guide](../CONTRIBUTING.md).
