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

## Backend Verification — 2026-11-22

| Command | Result |
|---|---|
| `python -m pytest -q` | **135 passed** |
| `python -m ruff check .` | Passed |
| `python manage.py makemigrations --check --dry-run` | Passed; no model changes or migration drift |
| `python manage.py spectacular --file ../docs/api_documentation/openapi.yaml --validate` | Passed; OpenAPI generated from the implemented review API |

The full backend suite uses PostgreSQL and includes assigned-candidate visibility, active membership and organization binding, review start, verified/rejected outcomes, audit attribution, command replay, and concurrent verification. The existing JWT, assignment, incident, machine-authentication, and throttle coverage also passed.

## Flutter Verification — 2026-11-22

| Command | Result |
|---|---|
| `flutter analyze --no-pub` | Passed; no issues found |
| `flutter test --no-pub` | Passed; 74 tests passed and 7 live-backend integration cases were skipped |

The seven environment-dependent live-backend integration cases were skipped because dedicated test server credentials and configuration were not present. Candidate review widget coverage exercises Police navigation, review start, verification retry with the same command ID, rejection rationale, data refresh, and the inactive-membership gate.

## Fixed Test Failures

- Login requests in different tests shared DRF's IP-based throttle history. Test settings now use a dedicated in-memory cache and an API-test fixture clears it before and after each case. The explicit test still verifies five login attempts are accepted by the throttle and the sixth receives HTTP 429; parameterized cases verify the budget resets between test invocations.
- DRF's stock scoped throttle expects a Django user with `is_authenticated` and `pk`. Machine authentication correctly supplies a `MachineActor`, which caused an `AttributeError` before the view ran. The AI ingestion route now uses a scoped throttle keyed by the verified machine service identity. Valid and invalid credentials are both covered, and body-supplied identity is ignored.

No Django migrations were added. Production throttle classes and limits were not changed; test cache isolation is configured only in `config.settings.test`.
