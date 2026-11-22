# Django Configuration

The package contains Django project entry points and settings for the local database foundation.

- `settings/base.py` defines installed apps, the custom account model, UTC timestamps, and PostgreSQL environment configuration.
- `settings/development.py` is local-only. It is not a deployment profile.
- `settings/test.py` uses PostgreSQL and a test-only secret/password hasher for the automated suite.
- Root `.env` is loaded only when present and is ignored by Git. Never place shared or production secrets in it.
- `urls.py` exposes only framework admin routing; application APIs are not implemented.
