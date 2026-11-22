"""Bounded, redacted HTTP client for the Django v1 AI event endpoint."""

import json
import logging
import os
import time
from collections.abc import Callable, Mapping
from http.client import HTTPResponse
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .contracts import DetectionEventPayload
from .errors import (
    BackendAuthenticationError,
    BackendAuthenticationUnavailable,
    BackendContractError,
    BackendIdempotencyConflict,
    BackendSourceRejected,
    BackendSubmissionError,
    BackendUnavailable,
    ConfigurationError,
)

logger = logging.getLogger(__name__)
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class MachineAuthenticator(Protocol):
    def headers(self) -> Mapping[str, str]: ...


class NoMachineAuthenticator:
    """Default policy: do not submit when machine identity is not configured."""

    def headers(self) -> Mapping[str, str]:
        raise BackendAuthenticationUnavailable(
            "Backend submissions are disabled until an approved machine authenticator is supplied."
        )


class ExplicitTestMachineTokenAuthenticator:
    """Explicit local/test adapter for the backend's test-only authenticator."""

    def __init__(self, token: str) -> None:
        if os.environ.get("RESQVISION_AI_TEST_MODE") != "1":
            raise BackendAuthenticationUnavailable("Test machine authentication is disabled.")
        if not token or any(character.isspace() for character in token):
            raise BackendAuthenticationUnavailable("A test machine token was not configured.")
        self._token = token

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None):
        values = os.environ if environ is None else environ
        if values.get("RESQVISION_AI_TEST_MODE") != "1":
            raise BackendAuthenticationUnavailable("Test machine authentication is disabled.")
        token = values.get("AI_TEST_MACHINE_TOKEN", "")
        if not token:
            raise BackendAuthenticationUnavailable("A test machine token was not configured.")
        authenticator = cls.__new__(cls)
        authenticator._token = token
        return authenticator

    def headers(self) -> Mapping[str, str]:
        return {"Authorization": f"Machine {self._token}"}


class BackendEventClient:
    def __init__(
        self,
        base_url: str,
        *,
        authenticator: MachineAuthenticator | None = None,
        timeout_seconds: float = 5.0,
        retry_attempts: int = 3,
        backoff_seconds: float = 0.25,
        opener: Callable[..., HTTPResponse] = urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ConfigurationError(
                "Backend base URL must be an HTTP(S) origin without credentials."
            )
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ConfigurationError(
                "Backend event submission requires HTTPS outside local development."
            )
        if timeout_seconds <= 0 or retry_attempts < 1 or backoff_seconds < 0:
            raise ConfigurationError("Backend timeout or retry configuration is invalid.")
        self.endpoint = base_url.rstrip("/") + "/api/v1/ai/detection-events/"
        self.authenticator = authenticator or NoMachineAuthenticator()
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.backoff_seconds = backoff_seconds
        self._opener = opener
        self._sleep = sleep

    def submit(self, payload: DetectionEventPayload) -> dict[str, str]:
        body = json.dumps(payload.to_mapping(), allow_nan=False, separators=(",", ":")).encode()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **self.authenticator.headers(),
        }
        request = Request(self.endpoint, data=body, headers=headers, method="POST")
        for attempt in range(1, self.retry_attempts + 1):
            try:
                with self._opener(request, timeout=self.timeout_seconds) as response:
                    result = json.loads(response.read().decode("utf-8"))
                if not isinstance(result, dict) or not {"id", "received_at"} <= result.keys():
                    raise BackendContractError(
                        "Backend response does not match the v1 response schema."
                    )
                logger.info(
                    "AI event accepted by backend",
                    extra={"event_id": payload.external_event_id, "attempt": attempt},
                )
                return {"id": str(result["id"]), "received_at": str(result["received_at"])}
            except HTTPError as exc:
                try:
                    error_code = json.loads(exc.read().decode("utf-8")).get("code")
                except (
                    AttributeError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ):
                    error_code = None
                if error_code == "machine_authentication_unavailable":
                    raise BackendAuthenticationUnavailable(
                        "Backend machine authentication is not configured."
                    ) from None
                if exc.code == 403 and error_code == "authorization_denied":
                    raise BackendSourceRejected(
                        "Backend rejected the source authorization or availability."
                    ) from None
                if exc.code == 404 and error_code == "not_found":
                    raise BackendSourceRejected(
                        "Backend could not resolve the configured video source."
                    ) from None
                if exc.code in _RETRYABLE_STATUS and attempt < self.retry_attempts:
                    logger.warning(
                        "Backend event request will be retried",
                        extra={
                            "event_id": payload.external_event_id,
                            "status_code": exc.code,
                            "attempt": attempt,
                        },
                    )
                    self._sleep(self.backoff_seconds * (2 ** (attempt - 1)))
                    continue
                if exc.code in {401, 403}:
                    raise BackendAuthenticationError(
                        "Backend rejected the machine identity."
                    ) from None
                if exc.code == 409:
                    raise BackendIdempotencyConflict(
                        "Backend reported an event identity conflict."
                    ) from None
                if exc.code in {400, 413, 422}:
                    raise BackendContractError(
                        "Backend rejected the event contract or payload."
                    ) from None
                if exc.code in _RETRYABLE_STATUS:
                    raise BackendUnavailable(
                        "Backend remained unavailable after bounded retries."
                    ) from None
                raise BackendSubmissionError("Backend rejected the event submission.") from None
            except (URLError, TimeoutError, OSError):
                if attempt < self.retry_attempts:
                    logger.warning(
                        "Backend event request will be retried after a transport failure",
                        extra={"event_id": payload.external_event_id, "attempt": attempt},
                    )
                    self._sleep(self.backoff_seconds * (2 ** (attempt - 1)))
                    continue
                raise BackendUnavailable(
                    "Backend could not be reached after bounded retries."
                ) from None
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BackendContractError("Backend returned an invalid JSON response.") from exc
        raise BackendUnavailable("Backend could not be reached after bounded retries.")
