import json
from datetime import UTC, datetime
from decimal import Decimal
from urllib.error import HTTPError, URLError
from uuid import uuid4

import pytest

from resqvision_ai.client import BackendEventClient, ExplicitTestMachineTokenAuthenticator
from resqvision_ai.config import AIServiceConfig
from resqvision_ai.contracts import DetectionEventPayload
from resqvision_ai.detectors import FrameDetection
from resqvision_ai.errors import (
    BackendAuthenticationUnavailable,
    BackendSourceRejected,
    BackendUnavailable,
    ConfigurationError,
)
from resqvision_ai.outbox import SQLiteEventOutbox
from resqvision_ai.publisher import EventPublisher
from resqvision_ai.service import build_ai_event_service
from resqvision_ai.video import VideoFrame


def payload():
    return DetectionEventPayload(
        video_source_id=uuid4(),
        external_event_id="simulated-integration-event",
        model_name="simulated-detector",
        model_version="test-1",
        detected_at=datetime(2026, 11, 22, tzinfo=UTC),
        processing_outcome="OBSERVATION",
        confidence=Decimal("0.9000"),
        auxiliary_metadata={"frame_index": 7},
    )


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        del args

    def read(self):
        return json.dumps(self.value).encode()


def test_client_retries_transient_failure_and_preserves_v1_contract():
    calls = []
    sleeps = []

    def opener(request, timeout):
        calls.append((request, timeout))
        if len(calls) == 1:
            raise URLError("sensitive transport detail")
        return FakeResponse({"id": "backend-uuid", "received_at": "2026-11-22T00:00:00Z"})

    client = BackendEventClient(
        "http://127.0.0.1:8000",
        authenticator=type(
            "Auth", (), {"headers": lambda self: {"Authorization": "Machine test"}}
        )(),
        timeout_seconds=2,
        retry_attempts=2,
        backoff_seconds=0.1,
        opener=opener,
        sleep=sleeps.append,
    )
    result = client.submit(payload())

    assert result["id"] == "backend-uuid"
    assert len(calls) == 2
    assert calls[0][1] == 2
    assert sleeps == [0.1]
    assert json.loads(calls[0][0].data)["contract_version"] == "v1"


def test_client_rejects_missing_machine_auth_before_network():
    called = False

    def opener(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("transport must not be called")

    client = BackendEventClient("http://localhost:8000", opener=opener)

    with pytest.raises(BackendAuthenticationUnavailable):
        client.submit(payload())
    assert not called


def test_test_machine_authenticator_requires_explicit_test_mode(monkeypatch):
    monkeypatch.delenv("RESQVISION_AI_TEST_MODE", raising=False)
    with pytest.raises(BackendAuthenticationUnavailable):
        ExplicitTestMachineTokenAuthenticator("explicit-test-only")

    monkeypatch.setenv("RESQVISION_AI_TEST_MODE", "1")
    auth = ExplicitTestMachineTokenAuthenticator("explicit-test-only")
    assert auth.headers() == {"Authorization": "Machine explicit-test-only"}


def test_client_refuses_plain_http_for_non_loopback_hosts():
    with pytest.raises(ConfigurationError):
        BackendEventClient("http://backend.example.test")


def test_outbox_publisher_keeps_failed_event_for_recovery(tmp_path):
    outbox = SQLiteEventOutbox(tmp_path / "events.sqlite3")
    event = payload()
    outbox.enqueue(event)

    class FailedClient:
        def submit(self, payload):
            del payload
            raise BackendUnavailable("offline")

    assert EventPublisher(outbox, FailedClient()).publish_pending() == (0, 1)
    assert outbox.pending_count() == 1
    assert outbox.pending()[0] == event
    outbox.record_failure(event, "safe_code")

    class SuccessfulClient:
        def submit(self, payload):
            return {"id": str(payload.video_source_id), "received_at": "now"}

    assert EventPublisher(outbox, SuccessfulClient()).publish_pending() == (1, 0)
    assert outbox.pending_count() == 0


def test_client_reports_exhausted_timeouts_without_leaking_transport_text():
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("secret URL or credential must not surface")

    auth = type("Auth", (), {"headers": lambda self: {"Authorization": "Machine test"}})()
    client = BackendEventClient(
        "http://localhost:8000",
        authenticator=auth,
        retry_attempts=2,
        backoff_seconds=0,
        opener=opener,
        sleep=lambda _: None,
    )
    with pytest.raises(BackendUnavailable, match="could not be reached"):
        client.submit(payload())
    assert len(calls) == 2


def test_client_does_not_retry_unconfigured_machine_auth_or_unauthorized_source():
    calls = []

    class ErrorBody:
        def __init__(self, value):
            self.value = value

        def read(self):
            return self.value

    def auth_unavailable(*args, **kwargs):
        calls.append(1)
        raise HTTPError(
            "http://localhost",
            503,
            "unavailable",
            {},
            ErrorBody(b'{"code":"machine_authentication_unavailable"}'),
        )

    auth = type("Auth", (), {"headers": lambda self: {"Authorization": "Machine test"}})()
    client = BackendEventClient(
        "http://localhost:8000",
        authenticator=auth,
        retry_attempts=3,
        opener=auth_unavailable,
        sleep=lambda _: None,
    )
    with pytest.raises(BackendAuthenticationUnavailable):
        client.submit(payload())
    assert len(calls) == 1

    def source_denied(*args, **kwargs):
        raise HTTPError(
            "http://localhost",
            403,
            "forbidden",
            {},
            ErrorBody(b'{"code":"authorization_denied"}'),
        )

    client._opener = source_denied
    with pytest.raises(BackendSourceRejected):
        client.submit(payload())


def test_composed_service_queues_observation_but_fails_closed_without_auth(tmp_path):
    config = AIServiceConfig(
        video_source_id=uuid4(),
        model_name="simulated-detector",
        model_version="test-only",
        confidence_threshold=0.5,
        observation_labels=frozenset({"collision"}),
        model_path=tmp_path / "no-model-included.pt",
        backend_base_url="http://localhost:8000",
        outbox_path=tmp_path / "service-outbox.sqlite3",
        request_retry_attempts=1,
    )

    class Detector:
        def infer(self, image):
            del image
            return [FrameDetection("collision", 0.9)]

    service = build_ai_event_service(config, detector=Detector())
    health = service.health()
    result = service.run([VideoFrame(index=0, captured_at=datetime.now(UTC), image=None)])

    assert health.ready is False
    assert health.checks["backend_machine_auth"]["error"] == (
        "approved_machine_authenticator_not_configured"
    )
    assert (result.delivered, result.failed) == (0, 1)
    assert service.publisher.outbox.pending_count() == 1
