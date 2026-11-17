"""Application checks for the public API boundary."""

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class ApiConfig(AppConfig):
    name = "api"
    verbose_name = "ResQVision API"

    def ready(self) -> None:
        signing_key = getattr(settings, "JWT_SIGNING_KEY", "")
        if not signing_key or len(signing_key) < 32:
            raise ImproperlyConfigured(
                "JWT_SIGNING_KEY must be configured with at least 32 characters."
            )
        if signing_key == settings.SECRET_KEY:
            raise ImproperlyConfigured("JWT_SIGNING_KEY must be separate from DJANGO_SECRET_KEY.")
