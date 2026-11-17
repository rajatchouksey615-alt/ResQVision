# API Testing Results

## Dependency and Static Verification

Compatibility was exercised in the project's isolated Python 3.14.10 environment with Django 5.2.19 and DRF 3.18.3 unchanged:

| Package/check | Result |
|---|---|
| `djangorestframework-simplejwt==5.5.1` | Installed/imported; Django checks pass |
| `drf-spectacular==0.30.0` | Installed/imported; generated OpenAPI schema validates with zero schema errors or warnings |
| `PyJWT==2.15.1` | Installed as the pinned SimpleJWT dependency |
| `manage.py check` | Passed |
| `manage.py makemigrations --check --dry-run` | Passed; no migration drift |
| `pip check` | Passed |
| `ruff check .` and `ruff format --check .` | Passed across the backend |
| `manage.py spectacular --validate` | Passed with zero schema errors or warnings |

## Latest PostgreSQL Run — 2026-11-17

| Command | Result |
|---|---|
| `python -m pytest api/tests/test_api.py -q` | **20 passed** |
| `python -m pytest -q` | **87 passed** |
| `python manage.py showmigrations` | All listed migrations applied |

The API suite uses PostgreSQL and covers JWT rotation/blacklisting, logout ownership, password-change revocation, scoped authorization, machine-authentication boundaries, throttling, and API integration behavior.

## Fixed Test Failures

- Login requests in different tests shared DRF's IP-based throttle history. Test settings now use a dedicated in-memory cache and an API-test fixture clears it before and after each case. The explicit test still verifies five login attempts are accepted by the throttle and the sixth receives HTTP 429; parameterized cases verify the budget resets between test invocations.
- DRF's stock scoped throttle expects a Django user with `is_authenticated` and `pk`. Machine authentication correctly supplies a `MachineActor`, which caused an `AttributeError` before the view ran. The AI ingestion route now uses a scoped throttle keyed by the verified machine service identity. Valid and invalid credentials are both covered, and body-supplied identity is ignored.

No Django migrations were added. Production throttle classes and limits were not changed; test cache isolation is configured only in `config.settings.test`.
