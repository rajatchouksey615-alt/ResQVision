"""Local end-to-end contract exercise using simulated frames and Django's API adapter."""

import io
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from uuid import uuid4

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

AI_SERVICE_SRC = Path(__file__).resolve().parents[3] / "ai_service" / "src"
if str(AI_SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_SRC))

from resqvision_ai.client import (  # noqa: E402
    BackendEventClient,
    ExplicitTestMachineTokenAuthenticator,
)
from resqvision_ai.detectors import FrameDetection  # noqa: E402
from resqvision_ai.outbox import SQLiteEventOutbox  # noqa: E402
from resqvision_ai.pipeline import DetectionPipeline  # noqa: E402
from resqvision_ai.publisher import EventPublisher  # noqa: E402
from resqvision_ai.service import AIEventService  # noqa: E402
from resqvision_ai.video import VideoFrame  # noqa: E402

from apps.detection.models import DetectionEvent  # noqa: E402
from apps.incidents.models import AccidentCandidate, AccidentIncident  # noqa: E402
from apps.sources.models import (  # noqa: E402
    VideoSourceAuthorizationStatus,
    VideoSourceAvailabilityStatus,
)


class SimulatedAccidentDetector:
    def infer(self, image):
        del image
        return [FrameDetection("vehicle_contact_observation", 0.93, (10, 12, 80, 90))]


class APIClientResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        del args

    def read(self):
        return self.content


class CapturingOutbox:
    def __init__(self, path):
        self.outbox = SQLiteEventOutbox(path)
        self.last_enqueued = None

    def enqueue(self, payload):
        self.last_enqueued = payload
        self.outbox.enqueue(payload)

    def pending(self, limit=100):
        return self.outbox.pending(limit)

    def record_failure(self, payload, safe_error_code):
        self.outbox.record_failure(payload, safe_error_code)

    def mark_delivered(self, payload):
        self.outbox.mark_delivered(payload)


@pytest.mark.django_db
def test_simulated_frame_to_backend_is_idempotent_and_stops_at_detection_event(
    user, video_source, tmp_path
):
    video_source.authorization_status = VideoSourceAuthorizationStatus.AUTHORIZED
    video_source.availability_status = VideoSourceAvailabilityStatus.AVAILABLE
    video_source.authorized_by_user = user
    video_source.authorized_at = timezone.now()
    video_source.authorization_reference = "explicit-local-test-approval"
    video_source.save(
        update_fields=[
            "authorization_status",
            "availability_status",
            "authorized_by_user",
            "authorized_at",
            "authorization_reference",
            "updated_at",
        ]
    )
    api = APIClient()
    token = f"local-test-{uuid4().hex}"

    def django_transport(request, timeout):
        assert timeout == 1
        response = api.generic(
            request.get_method(),
            "/api/v1/ai/detection-events/",
            data=request.data,
            content_type="application/json",
            HTTP_AUTHORIZATION=request.get_header("Authorization"),
        )
        if response.status_code >= 400:
            raise HTTPError(
                request.full_url,
                response.status_code,
                "local API response",
                {},
                io.BytesIO(response.content),
            )
        return APIClientResponse(response.content)

    authenticator = ExplicitTestMachineTokenAuthenticator.from_environment(
        {"RESQVISION_AI_TEST_MODE": "1", "AI_TEST_MACHINE_TOKEN": token}
    )
    client = BackendEventClient(
        "http://localhost:8000",
        authenticator=authenticator,
        timeout_seconds=1,
        retry_attempts=1,
        opener=django_transport,
    )
    outbox = CapturingOutbox(tmp_path / "integration-events.sqlite3")
    pipeline = DetectionPipeline(
        source_id=video_source.pk,
        model_name="simulated-detector",
        model_version="test-only",
        confidence_threshold=0.8,
        observation_labels=frozenset({"vehicle_contact_observation"}),
        detector=SimulatedAccidentDetector(),
        event_sink=outbox,
    )
    publisher = EventPublisher(outbox, client)
    service = AIEventService(pipeline, publisher)

    with override_settings(
        TESTING=True,
        AI_SERVICE_AUTHENTICATOR="api.v1.authentication.TestMachineCredentialAuthenticator",
        AI_TEST_MACHINE_TOKEN=token,
    ):
        result = service.run(
            [
                VideoFrame(
                    index=1,
                    captured_at=datetime(2026, 11, 22, 8, 30, tzinfo=UTC),
                    image=object(),
                )
            ]
        )
        assert result.processing.frames_processed == 1
        assert result.processing.events_generated == 1
        assert (result.delivered, result.failed) == (1, 0)

        replay = outbox.last_enqueued
        outbox.enqueue(replay)
        assert publisher.publish_pending() == (1, 0)

    event = DetectionEvent.objects.get(video_source=video_source)
    assert event.model_name == "simulated-detector"
    assert event.auxiliary_metadata["detections"][0]["label"] == ("vehicle_contact_observation")
    assert DetectionEvent.objects.filter(video_source=video_source).count() == 1
    assert not AccidentCandidate.objects.exists()
    assert not AccidentIncident.objects.exists()
