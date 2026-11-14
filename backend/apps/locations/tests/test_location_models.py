import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.locations.models import LocationCorrectionHistory, LocationRecord


def location_values(candidate, **overrides):
    values = {
        "subject_candidate": candidate,
        "claim_kind": LocationRecord.ClaimKind.ACCIDENT_LOCATION,
        "source_method": LocationRecord.SourceMethod.INFERRED,
        "created_by_service_ref": "AI_SERVICE",
        "latitude": "40.712800",
        "longitude": "-74.006000",
        "accuracy_m": "12.50",
    }
    values.update(overrides)
    return values


@pytest.mark.django_db
def test_location_claim_keeps_subject_distinct_from_provenance(
    candidate, video_source, detection_event
):
    location = LocationRecord.objects.create(
        **location_values(
            candidate,
            source_video_source=video_source,
            source_detection_event=detection_event,
        )
    )

    assert location.subject_candidate_id == candidate.pk
    assert location.source_video_source_id == video_source.pk
    assert location.source_detection_event_id == detection_event.pk
    assert location.claim_kind == LocationRecord.ClaimKind.ACCIDENT_LOCATION


@pytest.mark.django_db
def test_location_requires_exactly_one_subject(candidate, video_source):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LocationRecord.objects.create(
                **location_values(candidate, subject_video_source=video_source)
            )


@pytest.mark.django_db
def test_location_rejects_invalid_coordinates(candidate):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LocationRecord.objects.create(**location_values(candidate, latitude="91.000000"))


@pytest.mark.django_db
def test_only_one_current_location_claim_exists_per_subject(candidate):
    LocationRecord.objects.create(**location_values(candidate))

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LocationRecord.objects.create(
                **location_values(candidate, latitude=None, longitude=None)
            )


@pytest.mark.django_db
def test_location_correction_is_validated_and_append_only(candidate, user):
    location = LocationRecord.objects.create(**location_values(candidate))
    correction = LocationCorrectionHistory.objects.create(
        location_record=location,
        corrected_by_user=user,
        previous_latitude="40.712800",
        previous_longitude="-74.006000",
        new_latitude="40.713000",
        new_longitude="-74.005800",
        reason="Reviewer corrected map pin.",
        corrected_at=timezone.now(),
    )

    correction.reason = "rewritten"
    with pytest.raises(ValidationError, match="append-only"):
        correction.save()
