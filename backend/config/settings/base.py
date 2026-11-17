"""Shared settings for the ResQVision Django project."""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_ROOT.parent
load_dotenv(REPOSITORY_ROOT / ".env", override=False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY", "")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "api.apps.ApiConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.organizations.apps.OrganizationsConfig",
    "apps.sources.apps.SourcesConfig",
    "apps.detection.apps.DetectionConfig",
    "apps.incidents.apps.IncidentsConfig",
    "apps.evidence.apps.EvidenceConfig",
    "apps.locations.apps.LocationsConfig",
    "apps.responses.apps.ResponsesConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.audit.apps.AuditConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.api.request_id.RequestIDMiddleware",
    "common.api.request_id.ApiErrorBoundaryMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "resqvision_dev"),
        "USER": os.environ.get("POSTGRES_USER", "resqvision_app"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/admin/login/"

DATA_UPLOAD_MAX_MEMORY_SIZE = 1_048_576
FILE_UPLOAD_MAX_MEMORY_SIZE = 1_048_576

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "api.v1.permissions.IsAuthenticatedHuman",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.api.exception_handler.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "common.api.pagination.StandardLimitOffsetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/minute",
        "refresh": "20/minute",
        "sensitive": "30/minute",
        "ai_ingestion": "60/minute",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "CHECK_USER_IS_ACTIVE": True,
    "CHECK_REVOKE_TOKEN": True,
    "TOKEN_OBTAIN_SERIALIZER": "api.v1.authentication.EmailTokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "api.v1.authentication.RevocationAwareTokenRefreshSerializer",
}

AI_SERVICE_AUTHENTICATOR = None

SPECTACULAR_SETTINGS = {
    "TITLE": "ResQVision API",
    "DESCRIPTION": (
        "Versioned transport API for the ResQVision prototype. Operations marked unavailable "
        "remain disabled until their authorization or infrastructure decisions are approved."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        }
    },
}
