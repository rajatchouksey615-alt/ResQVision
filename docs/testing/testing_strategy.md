# Testing Strategy

**Status:** Project-wide strategy template.

Use test-driven development for feature work: define expected behavior, write a focused failing test, implement the smallest change, and run relevant checks. Review tests and behavior together.

## Test Levels

- Unit: isolated domain rules, utility behavior, verification logic, and widgets.
- Integration: interactions with databases, storage adapters, service contracts, and external boundaries using controlled test doubles where appropriate.
- API: validation, authentication, authorization, response schemas, and error behavior.
- UI and workflow: key mobile widget and integration flows.
- AI evaluation: approved, documented datasets and metrics for false positives, false negatives, and verification behavior.

Keep fixtures synthetic or otherwise approved and privacy-safe. Do not use real incident footage or personal data without documented authorization. Record what was run and its result; do not fabricate test outcomes. Agree on CI checks and coverage targets before setting thresholds.
