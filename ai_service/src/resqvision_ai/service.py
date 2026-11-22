"""Composition root for one configured video source and its event outbox."""

from collections.abc import Iterable
from dataclasses import dataclass

from .client import BackendEventClient, MachineAuthenticator, NoMachineAuthenticator
from .config import AIServiceConfig
from .detectors import UltralyticsYoloDetector
from .health import HealthReport, service_health
from .outbox import SQLiteEventOutbox
from .pipeline import DetectionPipeline, Detector, PipelineResult
from .publisher import EventPublisher
from .video import VideoFrame


@dataclass(frozen=True, slots=True)
class ServiceRunResult:
    processing: PipelineResult
    delivered: int
    failed: int


class AIEventService:
    def __init__(self, pipeline: DetectionPipeline, publisher: EventPublisher) -> None:
        self.pipeline = pipeline
        self.publisher = publisher

    def run(self, frames: Iterable[VideoFrame]) -> ServiceRunResult:
        processing = self.pipeline.process(frames)
        delivered, failed = self.publisher.publish_pending()
        return ServiceRunResult(processing=processing, delivered=delivered, failed=failed)

    def health(self) -> HealthReport:
        return service_health(
            configuration_valid=True,
            model_available=self.pipeline.detector is not None,
            video_source_configured=self.pipeline.source_id is not None,
            backend_authenticator_configured=not isinstance(
                self.publisher.client.authenticator, NoMachineAuthenticator
            ),
            outbox_writable=self.publisher.outbox.is_writable(),
        )


def build_ai_event_service(
    config: AIServiceConfig,
    *,
    authenticator: MachineAuthenticator | None = None,
    detector: Detector | None = None,
) -> AIEventService:
    """Compose the configured pipeline; absent machine auth remains fail-closed."""

    selected_detector = (
        detector if detector is not None else UltralyticsYoloDetector(config.model_path)
    )
    outbox = SQLiteEventOutbox(config.outbox_path)
    client = BackendEventClient(
        config.backend_base_url,
        authenticator=authenticator,
        timeout_seconds=config.request_timeout_seconds,
        retry_attempts=config.request_retry_attempts,
        backoff_seconds=config.retry_backoff_seconds,
    )
    pipeline = DetectionPipeline(
        source_id=config.video_source_id,
        model_name=config.model_name,
        model_version=config.model_version,
        confidence_threshold=config.confidence_threshold,
        observation_labels=config.observation_labels,
        detector=selected_detector,
        event_sink=outbox,
    )
    return AIEventService(pipeline, EventPublisher(outbox, client))
