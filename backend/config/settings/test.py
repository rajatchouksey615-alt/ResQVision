"""Automated-test settings using the same PostgreSQL backend as development."""

from .development import *  # noqa: F403

DEBUG = False
SECRET_KEY = "resqvision-test-only-key-not-for-production"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
