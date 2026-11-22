"""Authorized video source registry, ownership, and availability metadata."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.organizations.models import Organization
from common.models import UUIDPrimaryKeyModel


class VideoSourceType(models.TextChoices):
    CONTROLLED_FILE = "CONTROLLED_FILE", "Controlled file"
    CAMERA_STREAM = "CAMERA_STREAM", "Camera stream"
    OTHER = "OTHER", "Other"


class VideoSourceAuthorizationStatus(models.TextChoices):
    PENDING_REVIEW = "PENDING_REVIEW", "Pending review"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    SUSPENDED = "SUSPENDED", "Suspended"
    REVOKED = "REVOKED", "Revoked"


class VideoSourceAvailabilityStatus(models.TextChoices):
    UNKNOWN = "UNKNOWN", "Unknown"
    AVAILABLE = "AVAILABLE", "Available"
    DEGRADED = "DEGRADED", "Degraded"
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"


class VideoSource(UUIDPrimaryKeyModel):
    SourceType = VideoSourceType
    AuthorizationStatus = VideoSourceAuthorizationStatus
    AvailabilityStatus = VideoSourceAvailabilityStatus

    source_code = models.CharField(max_length=128)
    name = models.CharField(max_length=200)
    source_type = models.CharField(max_length=24, choices=VideoSourceType.choices)
    owner_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="video_sources",
    )
    designated_police_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="routed_video_sources",
    )
    owner_external_ref = models.CharField(max_length=128, null=True, blank=True)
    authorization_status = models.CharField(
        max_length=20,
        choices=VideoSourceAuthorizationStatus.choices,
        default=VideoSourceAuthorizationStatus.PENDING_REVIEW,
    )
    availability_status = models.CharField(
        max_length=16,
        choices=VideoSourceAvailabilityStatus.choices,
        default=VideoSourceAvailabilityStatus.UNKNOWN,
    )
    authorized_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="authorized_video_sources",
    )
    authorized_at = models.DateTimeField(null=True, blank=True)
    authorization_reference = models.CharField(max_length=256, null=True, blank=True)
    configuration_ref = models.CharField(max_length=256, null=True, blank=True)
    processing_policy_ref = models.CharField(max_length=100)
    retention_policy_ref = models.CharField(max_length=100)
    last_health_check_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sources_video_source"
        constraints = [
            models.UniqueConstraint(fields=["source_code"], name="uq_video_source_code"),
            models.CheckConstraint(
                condition=Q(source_type__in=VideoSourceType.values),
                name="ck_source_type",
            ),
            models.CheckConstraint(
                condition=(
                    Q(authorization_status__in=VideoSourceAuthorizationStatus.values)
                    & Q(availability_status__in=VideoSourceAvailabilityStatus.values)
                    & (
                        Q(
                            authorization_status=VideoSourceAuthorizationStatus.AUTHORIZED,
                            authorized_by_user__isnull=False,
                            authorized_at__isnull=False,
                        )
                        | (
                            ~Q(authorization_status=VideoSourceAuthorizationStatus.AUTHORIZED)
                            & Q(
                                authorized_by_user__isnull=True,
                                authorized_at__isnull=True,
                            )
                        )
                    )
                ),
                name="ck_source_states",
            ),
            models.CheckConstraint(
                condition=(
                    Q(owner_organization__isnull=False)
                    | (
                        Q(owner_external_ref__isnull=False)
                        & ~Q(owner_external_ref="")
                        & ~Q(owner_external_ref__regex=r"^\s*$")
                    )
                ),
                name="ck_source_owner_ref",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(source_code__regex=r"^\s*$")
                    & ~Q(name__regex=r"^\s*$")
                    & ~Q(processing_policy_ref__regex=r"^\s*$")
                    & ~Q(retention_policy_ref__regex=r"^\s*$")
                ),
                name="ck_source_nonblank_fields",
            ),
        ]
        indexes = [
            models.Index(
                fields=["authorization_status", "availability_status", "updated_at"],
                name="ix_source_auth_availability",
            ),
            models.Index(
                fields=["availability_status", "last_health_check_at"],
                name="ix_source_availability_health",
            ),
        ]

    def clean(self):
        super().clean()
        if self.authorization_status == self.AuthorizationStatus.AUTHORIZED:
            if not self.authorized_by_user_id or not self.authorized_at:
                raise ValidationError(
                    "An authorized source must have an approving user and timestamp."
                )
        elif self.authorized_by_user_id or self.authorized_at:
            raise ValidationError(
                "Current approval fields must be cleared while the source is not authorized."
            )

    def save(self, *args, **kwargs):
        self.source_code = self.source_code.strip()
        self.name = self.name.strip()
        if self.owner_external_ref is not None:
            self.owner_external_ref = self.owner_external_ref.strip() or None
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.source_code}: {self.name}"
