from uuid import uuid4

import pytest

from resqvision_ai.config import AIServiceConfig
from resqvision_ai.errors import ConfigurationError
from resqvision_ai.health import service_health


def valid_environment():
    return {
        "RESQVISION_VIDEO_SOURCE_ID": str(uuid4()),
        "RESQVISION_MODEL_NAME": "configured-model",
        "RESQVISION_MODEL_VERSION": "reviewed-version",
        "RESQVISION_CONFIDENCE_THRESHOLD": "0.72",
        "RESQVISION_OBSERVATION_LABELS": "collision, rollover",
        "RESQVISION_MODEL_PATH": "models/externally-provided.pt",
        "RESQVISION_BACKEND_BASE_URL": "https://backend.example.test",
        "RESQVISION_OUTBOX_PATH": "var/events.sqlite3",
    }


def test_config_requires_threshold_and_model_provenance_without_defaults():
    env = valid_environment()
    del env["RESQVISION_CONFIDENCE_THRESHOLD"]

    with pytest.raises(ConfigurationError, match="RESQVISION_CONFIDENCE_THRESHOLD"):
        AIServiceConfig.from_environment(env)


def test_config_parses_explicit_source_model_threshold_and_retry_settings():
    env = valid_environment()
    env["RESQVISION_REQUEST_TIMEOUT_SECONDS"] = "3.5"
    env["RESQVISION_REQUEST_RETRY_ATTEMPTS"] = "4"

    config = AIServiceConfig.from_environment(env)

    assert str(config.video_source_id) == env["RESQVISION_VIDEO_SOURCE_ID"]
    assert config.confidence_threshold == 0.72
    assert config.observation_labels == frozenset({"collision", "rollover"})
    assert config.request_timeout_seconds == 3.5
    assert config.request_retry_attempts == 4


def test_config_rejects_out_of_range_threshold():
    env = valid_environment()
    env["RESQVISION_CONFIDENCE_THRESHOLD"] = "1.1"

    with pytest.raises(ConfigurationError):
        AIServiceConfig.from_environment(env)


def test_health_report_explains_fail_closed_backend_and_model_status():
    report = service_health(
        configuration_valid=True,
        model_available=False,
        video_source_configured=True,
        backend_authenticator_configured=False,
        outbox_writable=True,
    )

    assert report.ready is False
    assert report.status == "not_ready"
    assert report.checks["model"]["error"] == "configured_model_unavailable"
    assert report.checks["backend_machine_auth"]["error"] == (
        "approved_machine_authenticator_not_configured"
    )
