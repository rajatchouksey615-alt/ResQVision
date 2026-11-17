# Mobile Application Architecture

## Status

Phase 5B adds human authentication and secure session management to the Phase 5A foundation. Android is the primary target; Windows supports desktop development. Web is not generated. The SDK constraint is Dart `^3.11.1`.

## Structure

```text
lib/
  main.dart
  app/
    app.dart
    bootstrap/
    router/
    theme/
  core/
    config/
    errors/
    logging/
    networking/
    security/
    widgets/
  features/
    authentication/
      application/
      data/
      presentation/
    dashboard/presentation/
test/
  unit/
  widget/
  integration/
```

`app` owns startup, the root widget, navigation, and design tokens. `core` owns reusable configuration, error mapping, logging, transport, and UI foundations. Feature-specific screens stay under `features`; the current dashboard feature contains only the foundation landing and prototype information screens. Future features should add layers when they have actual responsibilities rather than creating empty folders.

## Decisions

- Bootstrap initializes Flutter, loads `APP_ENV` and `API_BASE_URL`, logs a safe startup event, and renders a friendly setup state if configuration fails.
- The API base URL is a required compile-time value. It is validated as an absolute HTTP or HTTPS URL, and production configuration requires HTTPS. The API version prefix is `/api/v1/`, as documented by the backend.
- `ApiClient` uses Dart's built-in `HttpClient`, JSON content negotiation, configurable connection/response timeouts, and stable network/timeout errors. `AuthRepository` implements the audited Django token, refresh, current-user, and logout contracts over this client.
- `AuthSessionController` owns startup, login, authenticated, refresh, expiry, and recoverable-error states. `SessionGate` keeps workspaces hidden until `/auth/me/` validates the backend identity.
- Access and refresh tokens are stored through `flutter_secure_storage`; Android backups are disabled so encrypted credentials are not restored without their platform key.
- `AuthenticatedApiClient` attaches Bearer access credentials to relative API paths, coordinates refresh into one shared operation, and retries safe read methods once after a 401. It does not refresh on 403 or 429.
- Roles and active organization memberships come from the authenticated user endpoint. They drive workspace placeholders only; the backend remains authoritative for permissions.
- The router uses Flutter's built-in `Navigator` with centralized home, login, About, and unknown-route handling. The session gate is the protected-entry boundary.
- Material 3 light and dark themes follow the system setting and centralize color, typography, spacing, input, card, and button styling. Shared widgets include loading, empty, error, buttons, text-field, card, section-heading, and confirmation-dialog foundations.
- Logging uses `dart:developer` and structured records containing timestamps, severity, safe event identifiers, and exception types. Exception messages and stack traces are not logged.
- No general state-management or dependency-injection framework is added. `ChangeNotifier` provides the small session state shared by bootstrap, navigation, and authentication UI.
- `flutter_secure_storage` is the only new runtime dependency. The HTTP client remains Dart's built-in `HttpClient` for Android and Windows. A Web target requires a separate browser-compatible transport decision.

## Boundaries

The backend remains the source of identity, authorization, and domain state. The mobile client must not connect directly to PostgreSQL or the AI service. Incident and assignment workflows, evidence, notifications, maps, and operational emergency dispatch remain outside Phase 5B. No real emergency service or agency is contacted.

## Local Development

Pass the versioned API base URL with `--dart-define=API_BASE_URL=...`; see the [mobile README](../README.md) for Android emulator, Windows, and physical-device examples. The repository does not configure a custom Django HTTP port; Django's development server default is `8000`. Do not place secrets in compile-time configuration. The backend `.env` file is not consumed by Flutter.

## Future Phase Handoff

Later features should use the shared authenticated API client and backend contract. Client route guards support navigation only; they do not replace backend authorization.
