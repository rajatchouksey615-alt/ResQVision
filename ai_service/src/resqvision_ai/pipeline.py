"""Frame processing and observation event generation, independent from transport."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from .contracts import DetectionEventPayload
from .detectors import FrameDetection
from .video import VideoFrame

logger = logging.getLogger(__name__)


class FrameSource(Protocol):
    def __iter__(self) -> Iterable[VideoFrame]: ...


class Detector(Protocol):
    def infer(self, image: Any) -> list[FrameDetection]: ...


class EventSink(Protocol):
    def enqueue(self, payload: DetectionEventPayload) -> None: ...


@dataclass(frozen=True, slots=True)
class PipelineResult:
    frames_processed: int
    events_generated: int


class DetectionPipeline:
    """Apply configured confidence filtering, create observations, and enqueue them."""

    def __init__(
        self,
        *,
        source_id: UUID,
        model_name: str,
        model_version: str,
        confidence_threshold: float,
        observation_labels: frozenset[str],
        detector: Detector,
        event_sink: EventSink,
    ) -> None:
        if not 0 <= confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be between zero and one")
        if not observation_labels or any(not label.strip() for label in observation_labels):
            raise ValueError("At least one nonblank observation label is required")
        self.source_id = source_id
        self.model_name = model_name
        self.model_version = model_version
        self.confidence_threshold = confidence_threshold
        self.observation_labels = observation_labels
        self.detector = detector
        self.event_sink = event_sink

    def process(self, frames: Iterable[VideoFrame]) -> PipelineResult:
        processed = 0
        generated = 0
        for frame in frames:
            processed += 1
            predictions = self.detector.infer(frame.image)
            accepted = [
                prediction
                for prediction in predictions
                if prediction.label in self.observation_labels
                and prediction.confidence >= self.confidence_threshold
            ]
            if not accepted:
                continue
            payload = self._event_for_frame(frame, accepted)
            self.event_sink.enqueue(payload)
            generated += 1
            logger.info(
                "AI observation queued",
                extra={
                    "event_id": payload.external_event_id,
                    "source_id": str(payload.video_source_id),
                    "frame_index": frame.index,
                    "detection_count": len(accepted),
                },
            )
        return PipelineResult(frames_processed=processed, events_generated=generated)

    def _event_for_frame(
        self, frame: VideoFrame, predictions: list[FrameDetection]
    ) -> DetectionEventPayload:
        metadata = {
            "frame_index": frame.index,
            "detections": [
                {
                    "label": prediction.label,
                    "confidence": round(prediction.confidence, 4),
                    "box_xyxy": list(prediction.box_xyxy) if prediction.box_xyxy else None,
                }
                for prediction in predictions
            ],
        }
        event = DetectionEventPayload(
            video_source_id=self.source_id,
            external_event_id=str(uuid4()),
            model_name=self.model_name,
            model_version=self.model_version,
            detected_at=(
                frame.captured_at if isinstance(frame.captured_at, datetime) else datetime.now(UTC)
            ),
            processing_outcome="OBSERVATION",
            confidence=Decimal(str(max(item.confidence for item in predictions))),
            auxiliary_metadata=metadata,
        )
        return replace(event, payload_sha256=event.content_digest())
