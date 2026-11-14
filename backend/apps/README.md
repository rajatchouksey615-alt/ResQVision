# Backend Applications

Each focused Django app owns one persistence domain. Database models and migrations are implemented for:

- `accounts`: custom human user model and Django-managed group seeding.
- `organizations`: agencies, source owners, and organization-scoped group memberships.
- `sources`: authorized video source registry.
- `detection`: accepted AI observation provenance and source-scoped idempotency.
- `incidents`: candidates, event association, human review, authoritative incidents, and incident history.
- `evidence`: private object metadata, typed associations, and upload sessions.
- `locations`: typed location claims and correction history.
- `responses`: independent target assignments, append-only activities, and assignment histories.
- `notifications`: simulated notifications and delivery attempts.
- `audit`: append-only cross-domain audit events.

No API endpoints, real emergency dispatch, object-storage provider, or AI-service integration is implemented in this phase. Keep business transitions and cross-row authorization in the owning domain service when Phase 3 begins.
