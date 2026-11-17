"""Local development settings; never use as a deployment configuration."""

import os

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "resqvision-local-development-key-not-for-production"  # noqa: F405
ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, "localhost", "127.0.0.1", "[::1]"]))  # noqa: F405
JWT_SIGNING_KEY = os.environ.get(
    "JWT_SIGNING_KEY", "resqvision-local-jwt-signing-key-not-for-production"
)
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": JWT_SIGNING_KEY}  # noqa: F405
