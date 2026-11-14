import pytest
from django.db import IntegrityError, transaction

from apps.detection.models import DetectionEvent


def event_values(video_source, **overrides):
    values = {
        "video_source": video_source,
        "external_event_id": "event-002",
        "service_principal_ref": "AI_SERVICE",
        "model_name": "demo-detector",
        "model_version": "1.0.0",
        "detected_at": "2026-11-14T12:00:00Z",
        "processing_outcome": DetectionEvent.ProcessingOutcome.UNCERTAIN,
        "confidence": "0.5000",
        "auxiliary_metadata": {"schema": 1},
    }
    values.update(overrides)
    return values


@pytest.mark.django_db
def test_event_preserves_ai_provenance_and_source_scoped_identity(detection_event):
    assert detection_event.video_source.source_code == "demo-camera-001"
    assert detection_event.service_principal_ref == "AI_SERVICE"
    assert detection_event.model_version == "1.0.0"


@pytest.mark.django_db
def test_duplicate_external_event_for_same_source_is_rejected(video_source, detection_event):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DetectionEvent.objects.create(
                **event_values(video_source, external_event_id=detection_event.external_event_id)
            )


@pytest.mark.django_db
def test_confidence_outside_unit_interval_is_rejected(video_source):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DetectionEvent.objects.create(**event_values(video_source, confidence="1.0001"))


@pytest.mark.django_db
def test_auxiliary_metadata_must_be_an_object(video_source):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DetectionEvent.objects.bulk_create(
                [DetectionEvent(**event_values(video_source, auxiliary_metadata=["invalid"]))]
            )
