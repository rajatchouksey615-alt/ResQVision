# Backend

**Status:** Phase 2B database foundation implemented. This Django project owns persistence for the ResQVision domain and uses PostgreSQL. It does not yet expose API endpoints or implement operational workflows.

## Implemented foundation

- Python version: `3.14.10` (`.python-version`). Runtime/development dependencies are pinned in `requirements/`.
- Django `5.2.19`, Django REST Framework `3.18.3`, and Psycopg `3.3.9`.
- Custom UUID-keyed Django user model selected before the first migration; email is the normalized unique login identifier and Django owns password hashing.
- Ten focused Django apps with models and migrations for accounts, organizations, video sources, detection events, candidates/incidents, evidence, locations, responses, notifications, and audit.
- PostgreSQL is configured from environment variables. Local settings read the ignored repository `.env`; no production credentials or database target are included.
- PostgreSQL-backed tests cover model constraints and persistence boundaries.

## Local commands

From this directory, create an isolated Python environment and install development requirements:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements\development.txt
```

Set a private repository-root `.env` using `.env.example`, then start either the dedicated PostgreSQL 18 service in [`compose.database.yml`](../infrastructure/docker/compose.database.yml) or an isolated PostgreSQL cluster matching the local connection settings. Do not point tests at a shared or production database.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest -q
```

`pytest` creates a separate test database from the configured local PostgreSQL database. The development DB role must be allowed to create that test database.

## Boundaries

- Django owns authoritative structured data and authorization decisions.
- Object storage is not configured; PostgreSQL stores evidence metadata only.
- AI service and mobile clients do not connect directly to PostgreSQL.
- Notifications and agency responses remain simulated. No real emergency integration is configured.
- See [database design](../docs/database_design/README.md), [local development](../docs/deployment/local_development.md), and the [API documentation index](../docs/api_documentation/README.md).
