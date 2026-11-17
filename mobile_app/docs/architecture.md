# Mobile Application Architecture

## Status

Phase 5A establishes the Flutter application foundation in this directory. Android is the primary target; Windows supports desktop development. Web was not supported by the prior placeholder and is not generated. The SDK constraint is Dart `^3.11.1`.

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
    widgets/
  features/
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
- `ApiClient` uses Dart's built-in `HttpClient`, JSON content negotiation, configurable connection/response timeouts, and stable network/timeout errors. It exposes transport responses without adding authentication or endpoint-specific business behavior. No API call is made by the shell.
- The router uses Flutter's built-in `Navigator` with centralized home and About routes plus a generic unknown-route screen. It has no authentication or role guards.
- Material 3 light and dark themes follow the system setting and centralize color, typography, spacing, input, card, and button styling. Shared widgets include loading, empty, error, buttons, text-field, card, section-heading, and confirmation-dialog foundations.
- Logging uses `dart:developer` and structured records containing timestamps, severity, safe event identifiers, and exception types. Exception messages and stack traces are not logged.
- No state-management or dependency-injection package is added: this shell has no cross-screen application state to manage. Local transient state can remain inside widgets until a feature requires a shared state approach.
- No new package dependencies are added. The HTTP client is built on Dart IO for the Android and Windows targets. A Web target requires a separate browser-compatible transport decision.

## Boundaries

The backend remains the source of identity, authorization, and domain state. The mobile client must not connect directly to PostgreSQL or the AI service. Authentication, token storage, role-based routing, incident and assignment workflows, evidence, notifications, maps, and operational emergency dispatch remain outside Phase 5A. No real emergency service or agency is contacted.

## Local Development

Pass the versioned API base URL with `--dart-define=API_BASE_URL=...`; see the [mobile README](../README.md) for Android emulator, Windows, and physical-device examples. The repository does not configure a custom Django HTTP port; Django's development server default is `8000`. Do not place secrets in compile-time configuration. The backend `.env` file is not consumed by Flutter.

## Future Phase Handoff

Phase 5B can add authentication data sources, secure token storage, session orchestration, and protected navigation without moving identity decisions into the client. Feature repositories should depend on the shared transport and backend contracts. The API client currently makes no authentication assumptions and does not attach credentials.
