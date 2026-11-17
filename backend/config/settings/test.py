"""Automated-test settings using the same PostgreSQL backend as development."""

from .development import *  # noqa: F403

DEBUG = False
SECRET_KEY = "resqvision-test-only-key-not-for-production"
JWT_SIGNING_KEY = "resqvision-test-only-jwt-signing-key-not-for-production"
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": JWT_SIGNING_KEY}  # noqa: F405
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
TESTING = True
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "resqvision-api-tests",
    }
}
