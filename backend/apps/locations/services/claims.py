"""Location claim creation, verification, and correction workflows."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_denied_action, record_successful_action
from apps.detection.models import DetectionEvent
from apps.incidents.models import (
    AccidentCandidate,
    AccidentIncident,
    CandidateDetectionEvent,
)
from apps.locations.models import (
    LocationClaimKind,
    LocationCorrectionHistory,
    LocationRecord,
    LocationSourceMethod,
    LocationVerificationStatus,
)
from apps.sources.models import VideoSource
from common.domain.actors import Actor, HumanActor, MachineActor
from common.domain.authorization import require_ai_service, require_human, require_known_actor
from common.domain.exceptions import (
    AuthorizationDenied,
    BusinessRuleViolation,
    InvalidStateTransition,
    PolicyNotConfigured,
    ResourceConflict,
    ResourceNotFound,
)
from common.domain.policies import AuthorizationPolicy, require_authorized


def _audit_denied(actor: Actor, location_id: UUID | None, operation: str) -> None:
    record_denied_action(
        actor=actor,
        action="DOMAIN_ACTION_DENIED",
        resource_type="LOCATION",
        resource_id=location_id,
        safe_context={"reason_code": operation},
    )


def _decimal_value(value: Decimal | str | int | float | None, places: int, label: str):
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
        normalized = parsed.quantize(Decimal(1).scaleb(-places))
    except (InvalidOperation, ValueError) as exc:
        raise BusinessRuleViolation(f"{label} must be a finite decimal value.") from exc
    if not parsed.is_finite() or normalized != parsed:
        raise BusinessRuleViolation(f"{label} exceeds the stored coordinate precision.")
    return normalized


def _validate_location_values(
    *,
    latitude: Decimal | str | int | float | None,
    longitude: Decimal | str | int | float | None,
    accuracy_m: Decimal | str | int | float | None,
    captured_at: datetime | None = None,
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    lat = _decimal_value(latitude, 6, "Latitude")
    lon = _decimal_value(longitude, 6, "Longitude")
    accuracy = _decimal_value(accuracy_m, 2, "Accuracy")
    if (lat is None) != (lon is None):
        raise BusinessRuleViolation("Latitude and longitude must be supplied together.")
    if lat is not None and not Decimal("-90") <= lat <= Decimal("90"):
        raise BusinessRuleViolation("Latitude must be between -90 and 90 degrees.")
    if lon is not None and not Decimal("-180") <= lon <= Decimal("180"):
        raise BusinessRuleViolation("Longitude must be between -180 and 180 degrees.")
    if accuracy is not None and accuracy < 0:
        raise BusinessRuleViolation("Location accuracy cannot be negative.")
    if accuracy is not None and lat is None:
        raise BusinessRuleViolation("Accuracy cannot be recorded without coordinates.")
    if captured_at is not None and (captured_at.tzinfo is None or captured_at.utcoffset() is None):
        raise BusinessRuleViolation("Location capture time must include a timezone.")
    return lat, lon, accuracy


def _lock_subject(
    *,
    subject_video_source_id: UUID | None,
    subject_candidate_id: UUID | None,
    subject_incident_id: UUID | None,
):
    ids = [subject_video_source_id, subject_candidate_id, subject_incident_id]
    if sum(value is not None for value in ids) != 1:
        raise BusinessRuleViolation("Exactly one location subject must be supplied.")
    if subject_video_source_id is not None:
        subject = VideoSource.objects.select_for_update().filter(pk=subject_video_source_id).first()
        if subject is None:
            raise ResourceNotFound("Video source was not found.")
        return subject
    if subject_candidate_id is not None:
        subject = (
            AccidentCandidate.objects.select_for_update().filter(pk=subject_candidate_id).first()
        )
        if subject is None:
            raise ResourceNotFound("Candidate was not found.")
        return subject
    subject = (
        AccidentIncident.objects.select_for_update()
        .select_related("candidate")
        .filter(pk=subject_incident_id)
        .first()
    )
    if subject is None:
        raise ResourceNotFound("Incident was not found.")
    return subject


def create_location_claim(
    *,
    actor: Actor,
    claim_kind: str,
    source_method: str,
    latitude: Decimal | str | int | float | None = None,
    longitude: Decimal | str | int | float | None = None,
    accuracy_m: Decimal | str | int | float | None = None,
    captured_at: datetime | None = None,
    subject_video_source_id: UUID | None = None,
    subject_candidate_id: UUID | None = None,
    subject_incident_id: UUID | None = None,
    source_video_source_id: UUID | None = None,
    source_detection_event_id: UUID | None = None,
    policy: AuthorizationPolicy | None = None,
) -> LocationRecord:
    """Create one current claim without converting camera position into accident position."""

    try:
        if isinstance(actor, HumanActor):
            user = require_human(actor)
            service_ref = None
        else:
            machine = require_ai_service(actor)
            if (
                claim_kind != LocationClaimKind.ACCIDENT_LOCATION
                or source_method != LocationSourceMethod.INFERRED
                or subject_candidate_id is None
            ):
                raise AuthorizationDenied(
                    "AI_SERVICE may submit only inferred candidate location claims."
                )
            user = None
            service_ref = machine.service_ref

        if claim_kind not in LocationClaimKind.values:
            raise BusinessRuleViolation("Unsupported location claim kind.")
        if source_method not in LocationSourceMethod.values:
            raise BusinessRuleViolation("Unsupported location source method.")
        if claim_kind == LocationClaimKind.CAMERA_POSITION:
            if subject_video_source_id is None or source_method not in {
                LocationSourceMethod.CAMERA,
                LocationSourceMethod.GPS,
                LocationSourceMethod.MANUAL,
            }:
                raise BusinessRuleViolation(
                    "Camera position claims require a video source subject."
                )
        elif subject_video_source_id is not None or source_method == LocationSourceMethod.CAMERA:
            raise BusinessRuleViolation(
                "Accident locations must be separate from camera position claims."
            )
        lat, lon, accuracy = _validate_location_values(
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy_m,
            captured_at=captured_at,
        )

        with transaction.atomic():
            subject = _lock_subject(
                subject_video_source_id=subject_video_source_id,
                subject_candidate_id=subject_candidate_id,
                subject_incident_id=subject_incident_id,
            )
            if isinstance(actor, HumanActor):
                require_authorized(policy, "location.create", actor, subject)
            source = None
            event = None
            if source_video_source_id is not None:
                source = VideoSource.objects.filter(pk=source_video_source_id).first()
                if source is None:
                    raise ResourceNotFound("Location provenance source was not found.")
            if source_detection_event_id is not None:
                event = (
                    DetectionEvent.objects.select_related("video_source")
                    .filter(pk=source_detection_event_id)
                    .first()
                )
                if event is None:
                    raise ResourceNotFound("Location provenance event was not found.")
                if source is not None and source.pk != event.video_source_id:
                    raise BusinessRuleViolation(
                        "Location source and event provenance do not match."
                    )
                source = event.video_source
            if subject_video_source_id is not None:
                if source is not None and source.pk != subject_video_source_id:
                    raise BusinessRuleViolation(
                        "Camera location provenance must match its subject."
                    )
                source = source or subject
            if event is not None and subject_candidate_id is not None:
                if not CandidateDetectionEvent.objects.filter(
                    candidate_id=subject_candidate_id, detection_event_id=event.pk
                ).exists():
                    raise BusinessRuleViolation(
                        "Location event is not associated with this candidate."
                    )
            if event is not None and subject_incident_id is not None:
                if not CandidateDetectionEvent.objects.filter(
                    candidate_id=subject.candidate_id, detection_event_id=event.pk
                ).exists():
                    raise BusinessRuleViolation(
                        "Location event is not associated with this incident."
                    )
            if isinstance(actor, MachineActor) and subject_candidate_id != subject.pk:
                raise AuthorizationDenied("AI_SERVICE cannot add incident-level location claims.")

            location = LocationRecord(
                subject_video_source=subject if subject_video_source_id is not None else None,
                subject_candidate=subject if subject_candidate_id is not None else None,
                subject_incident=subject if subject_incident_id is not None else None,
                source_video_source=source,
                source_detection_event=event,
                claim_kind=claim_kind,
                source_method=source_method,
                latitude=lat,
                longitude=lon,
                accuracy_m=accuracy,
                captured_at=captured_at,
                created_by_user=user,
                created_by_service_ref=service_ref,
            )
            location.full_clean()
            location.save()
            record_successful_action(
                actor=actor,
                action="LOCATION_CREATED",
                resource_type="LOCATION",
                resource_id=location.pk,
                safe_context={
                    "source_id": source.pk if source else None,
                    "event_id": event.pk if event else None,
                    "candidate_id": subject.pk if subject_candidate_id else None,
                    "incident_id": subject.pk if subject_incident_id else None,
                },
            )
            return location
    except AuthorizationDenied, PolicyNotConfigured, BusinessRuleViolation:
        _audit_denied(actor, None, "location.create")
        raise
    except IntegrityError as exc:
        _audit_denied(actor, None, "location.create.conflict")
        raise ResourceConflict("A current location claim already exists for this subject.") from exc


def verify_location_claim(
    *,
    location_id: UUID,
    actor: Actor,
    policy: AuthorizationPolicy | None = None,
) -> LocationRecord:
    try:
        user = require_human(actor)
        with transaction.atomic():
            location = LocationRecord.objects.select_for_update().filter(pk=location_id).first()
            if location is None:
                raise ResourceNotFound("Location claim was not found.")
            require_authorized(policy, "location.verify", actor, location)
            if not location.is_current:
                raise InvalidStateTransition("Only the current location claim can be verified.")
            if location.verification_status == LocationVerificationStatus.VERIFIED:
                if location.verified_by_user_id == user.pk:
                    return location
                raise InvalidStateTransition("Location claim has already been verified.")
            if location.verification_status == LocationVerificationStatus.CORRECTED:
                raise InvalidStateTransition("A corrected location claim cannot be re-verified.")
            location.verification_status = LocationVerificationStatus.VERIFIED
            location.verified_by_user = user
            location.verified_at = timezone.now()
            location.save(update_fields=["verification_status", "verified_by_user", "verified_at"])
            record_successful_action(
                actor=actor,
                action="LOCATION_VERIFIED",
                resource_type="LOCATION",
                resource_id=location.pk,
                safe_context={"location_id": location.pk},
            )
            return location
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition:
        _audit_denied(actor, location_id, "location.verify")
        raise


def correct_location_claim(
    *,
    location_id: UUID,
    actor: Actor,
    latitude: Decimal | str | int | float | None,
    longitude: Decimal | str | int | float | None,
    accuracy_m: Decimal | str | int | float | None,
    reason: str,
    policy: AuthorizationPolicy | None = None,
) -> LocationRecord:
    try:
        user = require_human(actor)
        if not reason or not reason.strip():
            raise BusinessRuleViolation("A correction rationale is required.")
        if len(reason.strip()) > 4000:
            raise BusinessRuleViolation("The correction rationale is too long.")
        lat, lon, accuracy = _validate_location_values(
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy_m,
        )
        with transaction.atomic():
            location = LocationRecord.objects.select_for_update().filter(pk=location_id).first()
            if location is None:
                raise ResourceNotFound("Location claim was not found.")
            require_authorized(policy, "location.correct", actor, location)
            if not location.is_current:
                raise InvalidStateTransition("Only the current location claim can be corrected.")
            if (
                location.latitude == lat
                and location.longitude == lon
                and location.accuracy_m == accuracy
            ):
                raise BusinessRuleViolation("The correction does not change the location claim.")
            LocationCorrectionHistory.objects.create(
                location_record=location,
                corrected_by_user=user,
                previous_latitude=location.latitude,
                previous_longitude=location.longitude,
                new_latitude=lat,
                new_longitude=lon,
                previous_accuracy_m=location.accuracy_m,
                new_accuracy_m=accuracy,
                reason=reason.strip(),
            )
            location.latitude = lat
            location.longitude = lon
            location.accuracy_m = accuracy
            location.verification_status = LocationVerificationStatus.CORRECTED
            location.verified_by_user = user
            location.verified_at = timezone.now()
            location.save(
                update_fields=[
                    "latitude",
                    "longitude",
                    "accuracy_m",
                    "verification_status",
                    "verified_by_user",
                    "verified_at",
                ]
            )
            record_successful_action(
                actor=actor,
                action="LOCATION_CORRECTED",
                resource_type="LOCATION",
                resource_id=location.pk,
                safe_context={"location_id": location.pk},
            )
            return location
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, BusinessRuleViolation:
        _audit_denied(actor, location_id, "location.correct")
        raise
    except IntegrityError as exc:
        _audit_denied(actor, location_id, "location.correct.conflict")
        raise ResourceConflict("Location correction conflicts with existing history.") from exc


def get_current_location_claim(
    *,
    actor: Actor,
    policy: AuthorizationPolicy | None = None,
    subject_video_source_id: UUID | None = None,
    subject_candidate_id: UUID | None = None,
    subject_incident_id: UUID | None = None,
) -> LocationRecord | None:
    require_known_actor(actor)
    ids = [subject_video_source_id, subject_candidate_id, subject_incident_id]
    if sum(value is not None for value in ids) != 1:
        raise BusinessRuleViolation("Exactly one location subject must be supplied.")
    filters = {"is_current": True}
    if subject_video_source_id is not None:
        filters["subject_video_source_id"] = subject_video_source_id
    elif subject_candidate_id is not None:
        filters["subject_candidate_id"] = subject_candidate_id
    else:
        filters["subject_incident_id"] = subject_incident_id
    location = LocationRecord.objects.filter(**filters).first()
    require_authorized(policy, "location.read", actor, location or tuple(ids))
    return location
