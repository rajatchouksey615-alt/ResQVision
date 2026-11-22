from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from resqvision_ai.detectors import FrameDetection
from resqvision_ai.errors import VideoIngestionError
from resqvision_ai.pipeline import DetectionPipeline
from resqvision_ai.video import OpenCVVideoSource, VideoFrame


class FakeDetector:
    def infer(self, image):
        del image
        return [
            FrameDetection("collision", 0.91, (1, 2, 3, 4)),
            FrameDetection("vehicle", 0.99),
        ]


class FakeOutbox:
    def __init__(self):
        self.events = []

    def enqueue(self, payload):
        self.events.append(payload)


def test_pipeline_filters_by_configured_threshold_and_emits_observation_metadata():
    outbox = FakeOutbox()
    pipeline = DetectionPipeline(
        source_id=uuid4(),
        model_name="simulated-yolo",
        model_version="test-1",
        confidence_threshold=0.8,
        observation_labels=frozenset({"collision"}),
        detector=FakeDetector(),
        event_sink=outbox,
    )
    frames = [
        VideoFrame(index=4, captured_at=datetime(2026, 11, 22, tzinfo=UTC), image=object()),
        VideoFrame(
            index=5, captured_at=datetime(2026, 11, 22, 0, 0, 1, tzinfo=UTC), image=object()
        ),
    ]

    result = pipeline.process(frames)

    assert result.frames_processed == 2
    assert result.events_generated == 2
    assert len(outbox.events) == 2
    event = outbox.events[0]
    assert event.video_source_id == pipeline.source_id
    assert event.model_name == "simulated-yolo"
    assert event.processing_outcome == "OBSERVATION"
    assert event.confidence == Decimal("0.9100")
    assert event.payload_sha256 == event.content_digest()
    assert event.auxiliary_metadata["frame_index"] == 4
    assert len(event.auxiliary_metadata["detections"]) == 1


def test_pipeline_does_not_emit_when_every_prediction_is_below_threshold():
    class LowConfidenceDetector:
        def infer(self, image):
            del image
            return [FrameDetection("vehicle", 0.49)]

    outbox = FakeOutbox()
    pipeline = DetectionPipeline(
        source_id=uuid4(),
        model_name="simulated-yolo",
        model_version="test-1",
        confidence_threshold=0.5,
        observation_labels=frozenset({"vehicle"}),
        detector=LowConfidenceDetector(),
        event_sink=outbox,
    )

    result = pipeline.process([VideoFrame(index=0, captured_at=datetime.now(UTC), image=None)])

    assert result.events_generated == 0
    assert outbox.events == []


class FakeCapture:
    def __init__(self, images, opened=True):
        self.images = iter(images)
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        try:
            return True, next(self.images)
        except StopIteration:
            return False, None

    def release(self):
        self.released = True


def test_opencv_source_yields_frames_and_always_releases_capture():
    capture = FakeCapture(["frame-1", "frame-2"])

    class CV2:
        @staticmethod
        def VideoCapture(locator):
            assert locator == "controlled-demo.mp4"
            return capture

    frames = list(OpenCVVideoSource("controlled-demo.mp4", cv2_module=CV2))

    assert [frame.index for frame in frames] == [0, 1]
    assert all(frame.captured_at.tzinfo is not None for frame in frames)
    assert capture.released


def test_opencv_source_reports_unavailable_input():
    capture = FakeCapture([], opened=False)

    class CV2:
        @staticmethod
        def VideoCapture(locator):
            del locator
            return capture

    with pytest.raises(VideoIngestionError):
        list(OpenCVVideoSource("missing-demo.mp4", cv2_module=CV2))
    assert capture.released
