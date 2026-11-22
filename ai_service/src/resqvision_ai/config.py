"""Environment configuration without embedded credentials or calibrated thresholds."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from .errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class AIServiceConfig:
    video_source_id: UUID
    model_name: str
    model_version: str
    confidence_threshold: float
    observation_labels: frozenset[str]
    model_path: Path
    backend_base_url: str
    outbox_path: Path
    request_timeout_seconds: float = 5.0
    request_retry_attempts: int = 3
    retry_backoff_seconds: float = 0.25

    @classmethod
    def from_environment(cls, environ: dict[str, str] | None = None) -> AIServiceConfig:
        values = os.environ if environ is None else environ
        required = (
            "RESQVISION_VIDEO_SOURCE_ID",
            "RESQVISION_MODEL_NAME",
            "RESQVISION_MODEL_VERSION",
            "RESQVISION_CONFIDENCE_THRESHOLD",
            "RESQVISION_OBSERVATION_LABELS",
            "RESQVISION_MODEL_PATH",
            "RESQVISION_BACKEND_BASE_URL",
            "RESQVISION_OUTBOX_PATH",
        )
        missing = [name for name in required if not values.get(name)]
        if missing:
            raise ConfigurationError(
                "Missing required AI service configuration: " + ", ".join(missing)
            )
        try:
            threshold = float(values["RESQVISION_CONFIDENCE_THRESHOLD"])
            timeout = float(values.get("RESQVISION_REQUEST_TIMEOUT_SECONDS", "5"))
            attempts = int(values.get("RESQVISION_REQUEST_RETRY_ATTEMPTS", "3"))
            backoff = float(values.get("RESQVISION_RETRY_BACKOFF_SECONDS", "0.25"))
            source_id = UUID(values["RESQVISION_VIDEO_SOURCE_ID"])
        except (ValueError, TypeError) as exc:
            raise ConfigurationError("AI service configuration contains an invalid value.") from exc
        if not 0 <= threshold <= 1:
            raise ConfigurationError(
                "RESQVISION_CONFIDENCE_THRESHOLD must be between zero and one."
            )
        model_name = values["RESQVISION_MODEL_NAME"].strip()
        model_version = values["RESQVISION_MODEL_VERSION"].strip()
        if not model_name or not model_version:
            raise ConfigurationError("Model name and version must be nonblank.")
        observation_labels = frozenset(
            label.strip()
            for label in values["RESQVISION_OBSERVATION_LABELS"].split(",")
            if label.strip()
        )
        if not observation_labels:
            raise ConfigurationError("At least one observation label must be configured.")
        if (
            timeout <= 0
            or timeout > 300
            or attempts < 1
            or attempts > 10
            or backoff < 0
            or backoff > 60
        ):
            raise ConfigurationError("Timeout, retry attempts, or retry backoff is invalid.")
        return cls(
            video_source_id=source_id,
            model_name=model_name,
            model_version=model_version,
            confidence_threshold=threshold,
            observation_labels=observation_labels,
            model_path=Path(values["RESQVISION_MODEL_PATH"]),
            backend_base_url=values["RESQVISION_BACKEND_BASE_URL"],
            outbox_path=Path(values["RESQVISION_OUTBOX_PATH"]),
            request_timeout_seconds=timeout,
            request_retry_attempts=attempts,
            retry_backoff_seconds=backoff,
        )
