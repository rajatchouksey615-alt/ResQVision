# Backend

The planned backend uses Python, Django, Django REST Framework, and PostgreSQL. It will provide the centralized API and own authentication, authorization, incident business logic, evidence metadata, and notification coordination. No Django project, API, database schema, or migrations are implemented in Phase 0.

## Planned Boundaries

- Keep business rules separate from API views and serializers.
- Validate all incoming data and authorize every protected operation on the server.
- Store structured application data and evidence metadata in PostgreSQL.
- Store media files in an object storage service selected later; do not store large media in Git.
- Coordinate with the AI service through a reviewed internal contract.
- Keep real emergency integrations disabled.

## Future Setup

Dependency files in requirements/ are placeholders. Select and pin dependencies when the backend phase begins, document the supported Python and PostgreSQL versions, then create the Django project in config/ and application modules in apps/. Do not install packages as part of Phase 0.

See the [configuration](config/README.md), [application module](apps/README.md), and [shared component](common/README.md) notes, plus the [API documentation index](../docs/api_documentation/README.md).
