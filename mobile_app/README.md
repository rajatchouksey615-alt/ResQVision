# Mobile App

The planned mobile client uses Flutter and Dart and will provide role-based interfaces for Admin, Police, and Hospital users. It is not initialized or implemented in Phase 0.

## Planned Responsibilities

- Present incident information and role-specific actions.
- Authenticate through the backend API and apply the server-provided authorization model.
- Handle loading, error, and empty states.
- Keep API communication separate from presentation and use secure storage for sensitive authentication tokens.

The app must not connect directly to PostgreSQL or to the AI service. Maps and push notification providers remain pending decisions. The academic prototype must not send real emergency alerts.

## Future Setup

After the team approves the mobile implementation phase, install the Flutter SDK using its official instructions, create the application in this directory, record the supported SDK version, and add dependency manifests and tests. Phase 0 intentionally does not run Flutter initialization or install packages.

## Layout

- docs/architecture.md: mobile boundaries and integration responsibilities.
- assets/: approved images, icons, and fonts.
- test/: unit, widget, and integration test areas.

See the [contribution guide](../CONTRIBUTING.md) and [project-wide testing strategy](../docs/testing/testing_strategy.md).
