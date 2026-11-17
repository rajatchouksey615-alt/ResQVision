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

`test/integration/live_backend_auth_test.dart` exercises login, profile retrieval, refresh rotation, restoration, logout, and revocation against a live Django server when `RESQVISION_TEST_API_BASE_URL`, `RESQVISION_TEST_EMAIL`, and `RESQVISION_TEST_PASSWORD` point to an isolated test account. It is skipped in the ordinary test run when these values are absent. The test never prints or persists the supplied password.

## Scope boundaries

This phase implements human login and session handling only. Incident or assignment workflows, push notifications, maps, AI integration, emergency dispatch, and production deployment remain out of scope. The backend remains authoritative for identity and authorization. No real emergency service, police, hospital, or ambulance dispatch is connected.

See [mobile architecture](docs/architecture.md), the [authentication contract and lifecycle](docs/authentication.md), the [project testing strategy](../docs/testing/testing_strategy.md), and the [contribution guide](../CONTRIBUTING.md).
