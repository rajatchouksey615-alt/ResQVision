"""Provenance-aware camera and accident location claims."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.detection.models import DetectionEvent
from apps.incidents.models import AccidentCandidate, AccidentIncident
from apps.sources.models import VideoSource
from common.models import AppendOnlyUUIDModel, UUIDPrimaryKeyModel


class LocationClaimKind(models.TextChoices):
    CAMERA_POSITION = "CAMERA_POSITION", "Camera position"
    ACCIDENT_LOCATION = "ACCIDENT_LOCATION", "Accident location"


class LocationSourceMethod(models.TextChoices):
    CAMERA = "CAMERA", "Camera"
    GPS = "GPS", "GPS"
    INFERRED = "INFERRED", "Inferred"
    MANUAL = "MANUAL", "Manual"


class LocationVerificationStatus(models.TextChoices):
    UNVERIFIED = "UNVERIFIED", "Unverified"
    VERIFIED = "VERIFIED", "Verified"
    CORRECTED = "CORRECTED", "Corrected"


class LocationRecord(UUIDPrimaryKeyModel):
    ClaimKind = LocationClaimKind
    SourceMethod = LocationSourceMethod
    VerificationStatus = LocationVerificationStatus

    subject_video_source = models.ForeignKey(
        VideoSource,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_index=False,
        related_name="location_claims",
    )
    subject_candidate = models.ForeignKey(
        AccidentCandidate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_index=False,
        related_name="location_claims",
    )
    subject_incident = models.ForeignKey(
        AccidentIncident,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_index=False,
        related_name="location_claims",
    )
    source_video_source = models.ForeignKey(
        VideoSource,
        on_delete=models.PROTECT,
        db_index=False,
        null=True,
        blank=True,
        related_name="location_provenance",
    )
    source_detection_event = models.ForeignKey(
        DetectionEvent,
        on_delete=models.PROTECT,
        db_index=False,
        null=True,
        blank=True,
        related_name="location_provenance",
    )
    claim_kind = models.CharField(max_length=20, choices=LocationClaimKind.choices)
    source_method = models.CharField(max_length=16, choices=LocationSourceMethod.choices)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    accuracy_m = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    verification_status = models.CharField(
        max_length=16,
        choices=LocationVerificationStatus.choices,
        default=LocationVerificationStatus.UNVERIFIED,
    )
    verified_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="verified_location_claims",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_location_claims",
    )
    created_by_service_ref = models.CharField(max_length=128, null=True, blank=True)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "locations_location_record"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_video_source"],
                condition=Q(is_current=True),
                name="uq_loc_current_source",
            ),
            models.UniqueConstraint(
                fields=["subject_candidate"],
                condition=Q(is_current=True),
                name="uq_loc_current_candidate",
            ),
            models.UniqueConstraint(
                fields=["subject_incident"],
                condition=Q(is_current=True),
                name="uq_loc_current_incident",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        subject_video_source__isnull=False,
                        subject_candidate__isnull=True,
                        subject_incident__isnull=True,
                    )
                    | Q(
                        subject_video_source__isnull=True,
                        subject_candidate__isnull=False,
                        subject_incident__isnull=True,
                    )
                    | Q(
                        subject_video_source__isnull=True,
                        subject_candidate__isnull=True,
                        subject_incident__isnull=False,
                    )
                ),
                name="ck_location_subject_xor",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        claim_kind=LocationClaimKind.CAMERA_POSITION,
                        subject_video_source__isnull=False,
                    )
                    | Q(
                        claim_kind=LocationClaimKind.ACCIDENT_LOCATION,
                        subject_video_source__isnull=True,
                    )
                ),
                name="ck_location_claim_subject",
            ),
            models.CheckConstraint(
                condition=Q(claim_kind__in=LocationClaimKind.values),
                name="ck_location_claim_kind",
            ),
            models.CheckConstraint(
                condition=Q(source_method__in=LocationSourceMethod.values),
                name="ck_location_source_method",
            ),
            models.CheckConstraint(
                condition=Q(verification_status__in=LocationVerificationStatus.values),
                name="ck_location_verification_status",
            ),
            models.CheckConstraint(
                condition=(
                    Q(latitude__isnull=True, longitude__isnull=True)
                    | Q(latitude__isnull=False, longitude__isnull=False)
                ),
                name="ck_location_coordinate_pair",
            ),
            models.CheckConstraint(
                condition=Q(latitude__isnull=True) | Q(latitude__gte=-90, latitude__lte=90),
                name="ck_location_latitude_range",
            ),
            models.CheckConstraint(
                condition=Q(longitude__isnull=True) | Q(longitude__gte=-180, longitude__lte=180),
                name="ck_location_longitude_range",
            ),
            models.CheckConstraint(
                condition=Q(accuracy_m__isnull=True) | Q(accuracy_m__gte=0),
                name="ck_location_accuracy_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(verified_by_user__isnull=True, verified_at__isnull=True)
                    | Q(verified_by_user__isnull=False, verified_at__isnull=False)
                ),
                name="ck_location_verifier_pair",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        verification_status=LocationVerificationStatus.UNVERIFIED,
                        verified_by_user__isnull=True,
                    )
                    | Q(
                        verification_status__in=[
                            LocationVerificationStatus.VERIFIED,
                            LocationVerificationStatus.CORRECTED,
                        ],
                        verified_by_user__isnull=False,
                    )
                ),
                name="ck_location_verification_actor",
            ),
            models.CheckConstraint(
                condition=(
                    Q(created_by_user__isnull=False, created_by_service_ref__isnull=True)
                    | Q(
                        created_by_user__isnull=True,
                        created_by_service_ref__isnull=False,
                        created_by_service_ref__regex=r"\S",
                    )
                ),
                name="ck_location_creator_xor",
            ),
        ]
        indexes = [
            models.Index(fields=["subject_video_source"], name="ix_loc_subject_source"),
            models.Index(fields=["subject_candidate"], name="ix_loc_subject_candidate"),
            models.Index(fields=["subject_incident"], name="ix_loc_subject_incident"),
            models.Index(fields=["source_video_source"], name="ix_loc_source_video"),
            models.Index(fields=["source_detection_event"], name="ix_loc_source_event"),
        ]

    def __str__(self) -> str:
        return f"{self.claim_kind} location {self.pk}"


class LocationCorrectionHistory(AppendOnlyUUIDModel):
    location_record = models.ForeignKey(
        LocationRecord,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="corrections",
    )
    corrected_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="location_corrections",
    )
    previous_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    previous_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    new_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    new_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    previous_accuracy_m = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    new_accuracy_m = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reason = models.TextField()
    corrected_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "locations_location_correction_history"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(previous_latitude__isnull=True, previous_longitude__isnull=True)
                    | Q(previous_latitude__isnull=False, previous_longitude__isnull=False)
                ),
                name="ck_loc_corr_previous_pair",
            ),
            models.CheckConstraint(
                condition=(
                    Q(new_latitude__isnull=True, new_longitude__isnull=True)
                    | Q(new_latitude__isnull=False, new_longitude__isnull=False)
                ),
                name="ck_loc_corr_new_pair",
            ),
            models.CheckConstraint(
                condition=Q(previous_latitude__isnull=True)
                | Q(previous_latitude__gte=-90, previous_latitude__lte=90),
                name="ck_loc_corr_prev_lat_range",
            ),
            models.CheckConstraint(
                condition=Q(previous_longitude__isnull=True)
                | Q(previous_longitude__gte=-180, previous_longitude__lte=180),
                name="ck_loc_corr_prev_lon_range",
            ),
            models.CheckConstraint(
                condition=Q(new_latitude__isnull=True)
                | Q(new_latitude__gte=-90, new_latitude__lte=90),
                name="ck_loc_corr_new_lat_range",
            ),
            models.CheckConstraint(
                condition=Q(new_longitude__isnull=True)
                | Q(new_longitude__gte=-180, new_longitude__lte=180),
                name="ck_loc_corr_new_lon_range",
            ),
            models.CheckConstraint(
                condition=(
                    (Q(previous_accuracy_m__isnull=True) | Q(previous_accuracy_m__gte=0))
                    & (Q(new_accuracy_m__isnull=True) | Q(new_accuracy_m__gte=0))
                    & Q(reason__regex=r"\S")
                ),
                name="ck_loc_corr_values_reason",
            ),
        ]
        indexes = [
            models.Index(
                fields=["location_record", "corrected_at"], name="ix_loc_corr_record_time"
            ),
            models.Index(
                fields=["corrected_by_user", "corrected_at"], name="ix_loc_corr_actor_time"
            ),
        ]
