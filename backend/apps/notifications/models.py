"""Application notices and simulated delivery attempts."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.incidents.models import AccidentIncident
from apps.responses.models import ResponseAssignment
from common.models import AppendOnlyUUIDModel, UUIDPrimaryKeyModel


class NotificationStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    PENDING = "PENDING", "Pending"
    DELIVERED_SIMULATED = "DELIVERED_SIMULATED", "Delivered simulated"
    FAILED = "FAILED", "Failed"
    READ = "READ", "Read"
    CANCELLED = "CANCELLED", "Cancelled"


class DeliveryOutcome(models.TextChoices):
    DELIVERED_SIMULATED = "DELIVERED_SIMULATED", "Delivered simulated"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class Notification(UUIDPrimaryKeyModel):
    Status = NotificationStatus

    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="notifications",
    )
    incident = models.ForeignKey(
        AccidentIncident,
        on_delete=models.PROTECT,
        db_index=False,
        null=True,
        blank=True,
        related_name="notifications",
    )
    response_assignment = models.ForeignKey(
        ResponseAssignment,
        on_delete=models.PROTECT,
        db_index=False,
        null=True,
        blank=True,
        related_name="notifications",
    )
    status = models.CharField(
        max_length=24,
        choices=NotificationStatus.choices,
        default=NotificationStatus.CREATED,
    )
    creation_command_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    safe_message_code = models.CharField(max_length=64)

    class Meta:
        db_table = "notifications_notification"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(incident__isnull=False, response_assignment__isnull=True)
                    | Q(incident__isnull=True, response_assignment__isnull=False)
                ),
                name="ck_notification_target_xor",
            ),
            models.CheckConstraint(
                condition=Q(status__in=NotificationStatus.values),
                name="ck_notification_status",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status=NotificationStatus.READ, read_at__isnull=False)
                    | Q(
                        status__in=[
                            NotificationStatus.CREATED,
                            NotificationStatus.PENDING,
                            NotificationStatus.DELIVERED_SIMULATED,
                            NotificationStatus.FAILED,
                            NotificationStatus.CANCELLED,
                        ],
                        read_at__isnull=True,
                    )
                ),
                name="ck_notification_read_time",
            ),
            models.CheckConstraint(
                condition=Q(safe_message_code__regex=r"\S"),
                name="ck_notification_message_code",
            ),
            models.UniqueConstraint(
                fields=["creation_command_id"],
                condition=Q(creation_command_id__isnull=False),
                name="uq_notification_command",
            ),
        ]
        indexes = [
            models.Index(
                fields=["recipient_user", "status", "created_at"], name="ix_notification_recipient"
            ),
            models.Index(
                fields=["incident"],
                condition=Q(incident__isnull=False),
                name="ix_notification_incident",
            ),
            models.Index(
                fields=["response_assignment"],
                condition=Q(response_assignment__isnull=False),
                name="ix_notification_assignment",
            ),
        ]


class NotificationDeliveryAttempt(AppendOnlyUUIDModel):
    Outcome = DeliveryOutcome

    notification = models.ForeignKey(
        Notification,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="delivery_attempts",
    )
    attempt_number = models.PositiveIntegerField()
    outcome = models.CharField(max_length=24, choices=DeliveryOutcome.choices)
    attempted_at = models.DateTimeField(default=timezone.now)
    safe_failure_code = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_delivery_attempt"
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "attempt_number"],
                name="uq_delivery_attempt_number",
            ),
            models.CheckConstraint(
                condition=Q(attempt_number__gt=0),
                name="ck_delivery_attempt_positive",
            ),
            models.CheckConstraint(
                condition=Q(outcome__in=DeliveryOutcome.values),
                name="ck_delivery_outcome",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        outcome=DeliveryOutcome.FAILED,
                        safe_failure_code__isnull=False,
                        safe_failure_code__regex=r"\S",
                    )
                    | Q(
                        outcome__in=[
                            DeliveryOutcome.DELIVERED_SIMULATED,
                            DeliveryOutcome.CANCELLED,
                        ]
                    )
                ),
                name="ck_delivery_failure_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["notification", "attempted_at"], name="ix_delivery_notification_time"
            ),
        ]
