"""Private evidence metadata and upload coordination records."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.detection.models import DetectionEvent
from apps.incidents.models import AccidentCandidate, AccidentIncident
from apps.sources.models import VideoSource
from common.models import UUIDPrimaryKeyModel


class EvidenceStatus(models.TextChoices):
    PENDING_UPLOAD = "PENDING_UPLOAD", "Pending upload"
    UPLOADING = "UPLOADING", "Uploading"
    QUARANTINED = "QUARANTINED", "Quarantined"
    AVAILABLE = "AVAILABLE", "Available"
    FAILED = "FAILED", "Failed"
    EXPIRED = "EXPIRED", "Expired"
    DELETED = "DELETED", "Deleted"


class EvidenceScanStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    NOT_REQUIRED = "NOT_REQUIRED", "Not required"
    PASSED = "PASSED", "Passed"
    FAILED = "FAILED", "Failed"


class UploadSessionStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    UPLOADING = "UPLOADING", "Uploading"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    EXPIRED = "EXPIRED", "Expired"
    REVOKED = "REVOKED", "Revoked"


class EvidenceAsset(UUIDPrimaryKeyModel):
    Status = EvidenceStatus
    ScanStatus = EvidenceScanStatus

    source_detection_event = models.ForeignKey(
        DetectionEvent,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evidence_assets",
    )
    created_by_service_ref = models.CharField(max_length=128, null=True, blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_evidence_assets",
    )
    storage_provider = models.CharField(max_length=40)
    storage_namespace = models.CharField(max_length=120)
    object_key = models.CharField(max_length=512)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    media_type = models.CharField(max_length=127, null=True, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    checksum_sha256 = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=EvidenceStatus.choices,
        default=EvidenceStatus.PENDING_UPLOAD,
    )
    scan_status = models.CharField(
        max_length=16,
        choices=EvidenceScanStatus.choices,
        default=EvidenceScanStatus.PENDING,
    )
    validation_completed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    retention_policy_ref = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "evidence_evidence_asset"
        constraints = [
            models.UniqueConstraint(
                fields=["storage_provider", "storage_namespace", "object_key"],
                name="uq_evidence_object_ref",
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
                name="ck_evidence_creator_xor",
            ),
            models.CheckConstraint(
                condition=Q(status__in=EvidenceStatus.values),
                name="ck_evidence_status",
            ),
            models.CheckConstraint(
                condition=Q(scan_status__in=EvidenceScanStatus.values),
                name="ck_evidence_scan_status",
            ),
            models.CheckConstraint(
                condition=Q(size_bytes__isnull=True) | Q(size_bytes__gt=0),
                name="ck_evidence_size_positive",
            ),
            models.CheckConstraint(
                condition=Q(checksum_sha256__isnull=True)
                | Q(checksum_sha256__regex=r"^[0-9a-f]{64}$"),
                name="ck_evidence_checksum",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status=EvidenceStatus.AVAILABLE)
                    & Q(
                        scan_status__in=[EvidenceScanStatus.NOT_REQUIRED, EvidenceScanStatus.PASSED]
                    )
                    & Q(validation_completed_at__isnull=False)
                    & Q(uploaded_at__isnull=False)
                    & Q(size_bytes__isnull=False)
                    & Q(size_bytes__gt=0)
                    & Q(checksum_sha256__isnull=False)
                    & Q(checksum_sha256__regex=r"^[0-9a-f]{64}$")
                    & Q(media_type__isnull=False)
                    & Q(media_type__regex=r"\S")
                    | ~Q(status=EvidenceStatus.AVAILABLE)
                ),
                name="ck_evidence_available_validated",
            ),
            models.CheckConstraint(
                condition=(~Q(status=EvidenceStatus.EXPIRED) | Q(expired_at__isnull=False))
                & (~Q(status=EvidenceStatus.DELETED) | Q(deleted_at__isnull=False)),
                name="ck_evidence_terminal_time",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="ix_evidence_status_created"),
        ]

    def __str__(self) -> str:
        return f"Evidence {self.pk} ({self.status})"


class EvidenceAssociation(UUIDPrimaryKeyModel):
    evidence_asset = models.ForeignKey(
        EvidenceAsset,
        on_delete=models.PROTECT,
        related_name="associations",
    )
    video_source = models.ForeignKey(
        VideoSource,
        on_delete=models.PROTECT,
        db_index=False,
        null=True,
        blank=True,
        related_name="evidence_associations",
    )
    candidate = models.ForeignKey(
        AccidentCandidate,
        on_delete=models.PROTECT,
        db_index=False,
        null=True,
        blank=True,
        related_name="evidence_associations",
    )
    incident = models.ForeignKey(
        AccidentIncident,
        on_delete=models.PROTECT,
        db_index=False,
        null=True,
        blank=True,
        related_name="evidence_associations",
    )
    associated_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evidence_associations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evidence_evidence_association"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(video_source__isnull=False, candidate__isnull=True, incident__isnull=True)
                    | Q(video_source__isnull=True, candidate__isnull=False, incident__isnull=True)
                    | Q(video_source__isnull=True, candidate__isnull=True, incident__isnull=False)
                ),
                name="ck_evidence_association_target_xor",
            ),
            models.UniqueConstraint(
                fields=["video_source"],
                condition=Q(video_source__isnull=False),
                name="uq_evidence_source_input",
            ),
            models.UniqueConstraint(
                fields=["evidence_asset", "candidate"],
                condition=Q(candidate__isnull=False),
                name="uq_evidence_candidate_link",
            ),
            models.UniqueConstraint(
                fields=["evidence_asset", "incident"],
                condition=Q(incident__isnull=False),
                name="uq_evidence_incident_link",
            ),
        ]
        indexes = [
            models.Index(fields=["candidate"], name="ix_evid_assoc_candidate"),
            models.Index(fields=["incident"], name="ix_evid_assoc_incident"),
        ]


class EvidenceUploadSession(UUIDPrimaryKeyModel):
    Status = UploadSessionStatus

    evidence_asset = models.ForeignKey(
        EvidenceAsset,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="upload_sessions",
    )
    service_ref = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16,
        choices=UploadSessionStatus.choices,
        default=UploadSessionStatus.CREATED,
    )
    authorized_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evidence_evidence_upload_session"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=UploadSessionStatus.values),
                name="ck_upload_session_status",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=models.F("created_at")),
                name="ck_upload_session_expiry_after_create",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status=UploadSessionStatus.AUTHORIZED, authorized_at__isnull=False)
                    | ~Q(status=UploadSessionStatus.AUTHORIZED)
                ),
                name="ck_upload_authorized_time",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status=UploadSessionStatus.COMPLETED, completed_at__isnull=False)
                    | ~Q(status=UploadSessionStatus.COMPLETED)
                ),
                name="ck_upload_completed_time",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=UploadSessionStatus.FAILED,
                        failure_code__isnull=False,
                        failure_code__regex=r"\S",
                    )
                    | ~Q(status=UploadSessionStatus.FAILED)
                ),
                name="ck_upload_failure_code",
            ),
            models.CheckConstraint(
                condition=Q(service_ref__regex=r"\S"),
                name="ck_upload_service_ref_nonblank",
            ),
            models.UniqueConstraint(
                fields=["evidence_asset"],
                condition=Q(
                    status__in=[
                        UploadSessionStatus.CREATED,
                        UploadSessionStatus.AUTHORIZED,
                        UploadSessionStatus.UPLOADING,
                    ]
                ),
                name="uq_upload_active_asset",
            ),
        ]
        indexes = [
            models.Index(fields=["evidence_asset", "created_at"], name="ix_upload_asset_time"),
            models.Index(fields=["status", "expires_at"], name="ix_upload_status_expiry"),
        ]
