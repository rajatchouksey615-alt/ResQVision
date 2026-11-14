"""Accepted AI observation records with source-scoped idempotency."""

from django.db import models
from django.db.models import F, Func, Q, Value
from django.db.models.lookups import Exact
from django.utils import timezone

from apps.sources.models import VideoSource
from common.models import UUIDPrimaryKeyModel


class EventProcessingOutcome(models.TextChoices):
    OBSERVATION = "OBSERVATION", "Observation"
    UNCERTAIN = "UNCERTAIN", "Uncertain observation"


class DetectionEvent(UUIDPrimaryKeyModel):
    ProcessingOutcome = EventProcessingOutcome

    video_source = models.ForeignKey(
        VideoSource,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="detection_events",
    )
    external_event_id = models.CharField(max_length=128)
    service_principal_ref = models.CharField(max_length=128)
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=100)
    detected_at = models.DateTimeField()
    received_at = models.DateTimeField(default=timezone.now)
    processing_outcome = models.CharField(max_length=20, choices=EventProcessingOutcome.choices)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    payload_sha256 = models.CharField(max_length=64, null=True, blank=True)
    metadata_schema_version = models.PositiveSmallIntegerField(default=1)
    auxiliary_metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "detection_detection_event"
        constraints = [
            models.UniqueConstraint(
                fields=["video_source", "external_event_id"],
                name="uq_event_source_external",
            ),
            models.CheckConstraint(
                condition=Q(processing_outcome__in=EventProcessingOutcome.values),
                name="ck_event_outcome",
            ),
            models.CheckConstraint(
                condition=Q(confidence__isnull=True) | Q(confidence__gte=0, confidence__lte=1),
                name="ck_event_confidence",
            ),
            models.CheckConstraint(
                condition=Q(payload_sha256__isnull=True)
                | Q(payload_sha256__regex=r"^[0-9a-f]{64}$"),
                name="ck_event_digest",
            ),
            models.CheckConstraint(
                condition=Q(metadata_schema_version__gte=1),
                name="ck_event_metadata_version",
            ),
            models.CheckConstraint(
                condition=Exact(
                    Func(
                        F("auxiliary_metadata"),
                        function="jsonb_typeof",
                        output_field=models.CharField(),
                    ),
                    Value("object"),
                ),
                name="ck_event_metadata_object",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(external_event_id__regex=r"^\s*$")
                    & ~Q(service_principal_ref__regex=r"^\s*$")
                    & ~Q(model_name__regex=r"^\s*$")
                    & ~Q(model_version__regex=r"^\s*$")
                ),
                name="ck_event_provenance_nonblank",
            ),
        ]
        indexes = [
            models.Index(
                fields=["video_source", "detected_at"],
                name="ix_event_source_detected",
            ),
            models.Index(fields=["received_at"], name="ix_event_received"),
        ]

    def __str__(self) -> str:
        return f"{self.video_source.source_code}:{self.external_event_id}"
