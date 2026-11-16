# Local Development Guide

**Status:** The local PostgreSQL/Django foundation and internal domain service modules are runnable. Application APIs and external integrations are not implemented.

## Planned Local Services

The implemented local environment supports the Django database foundation with PostgreSQL 18.7. `infrastructure/docker/compose.database.yml` defines an optional database container bound to loopback port 5433. If Docker Engine is unavailable, use a dedicated local PostgreSQL instance on that port. No mobile app, AI service, object-storage provider, or emergency-service connection is configured.

## Setup Conventions

1. Install Python 3.14.10 and create the backend environment from `backend/README.md`.
2. Create a private repository-root `.env` from `.env.example`, then replace placeholder values with local-only credentials. The file is ignored by Git.
3. Start only the dedicated local PostgreSQL database, either with the Compose file or a separate local cluster on port 5433. The configured role/database default to `resqvision_app`/`resqvision_dev`; do not point development or tests at a shared or production database.
4. From `backend/`, run `python manage.py migrate`, `python manage.py check`, and `python -m pytest -q` using the project virtual environment. Pytest creates a separate test database.
5. Use synthetic data only and stop local database services when finished.

Map, object storage, and Firebase providers are not configured. Do not connect the prototype to real emergency services.
