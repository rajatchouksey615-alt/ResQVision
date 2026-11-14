"""Local development settings; never use as a deployment configuration."""

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "resqvision-local-development-key-not-for-production"  # noqa: F405
ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, "localhost", "127.0.0.1", "[::1]"]))  # noqa: F405
