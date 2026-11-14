"""Independent per-organization assignments and simulated response activity."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.incidents.models import AccidentIncident
from apps.organizations.models import Organization
from common.models import AppendOnlyUUIDModel, UUIDPrimaryKeyModel


class AssignmentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    UNABLE_TO_RESPOND = "UNABLE_TO_RESPOND", "Unable to respond"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class ResponseActivityKind(models.TextChoices):
    PROGRESS_UPDATE = "PROGRESS_UPDATE", "Progress update"
    READINESS_UPDATE = "READINESS_UPDATE", "Readiness update"
    COMPLETION_NOTE = "COMPLETION_NOTE", "Completion note"
    UNABLE_TO_RESPOND_NOTE = "UNABLE_TO_RESPOND_NOTE", "Unable to respond note"
    GENERAL_NOTE = "GENERAL_NOTE", "General note"


class ResponseAssignment(UUIDPrimaryKeyModel):
    Status = AssignmentStatus

    incident = models.ForeignKey(
        AccidentIncident,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="response_assignments",
    )
    target_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="response_assignments",
    )
    assigned_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_response_assignments",
    )
    replacement_for = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_index=False,
        related_name="replacement",
    )
    creation_command_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=24,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "responses_response_assignment"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=AssignmentStatus.values),
                name="ck_assignment_status",
            ),
            models.UniqueConstraint(
                fields=["creation_command_id"],
                condition=Q(creation_command_id__isnull=False),
                name="uq_assignment_command",
            ),
            models.UniqueConstraint(
                fields=["replacement_for"],
                condition=Q(replacement_for__isnull=False),
                name="uq_assignment_replacement",
            ),
            models.UniqueConstraint(
                fields=["incident", "target_organization"],
                condition=Q(
                    status__in=[
                        AssignmentStatus.PENDING,
                        AssignmentStatus.ACKNOWLEDGED,
                        AssignmentStatus.IN_PROGRESS,
                    ]
                ),
                name="uq_assignment_active_target",
            ),
        ]
        indexes = [
            models.Index(fields=["incident", "status"], name="ix_assignment_incident_status"),
            models.Index(
                fields=["target_organization", "status", "created_at"],
                name="ix_assignment_target_queue",
            ),
            models.Index(fields=["incident", "created_at"], name="ix_assignment_incident_time"),
        ]

    def __str__(self) -> str:
        return f"{self.incident_id} -> {self.target_organization_id} ({self.status})"


class Response(AppendOnlyUUIDModel):
    ActivityKind = ResponseActivityKind

    response_assignment = models.ForeignKey(
        ResponseAssignment,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="activities",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="response_activities",
    )
    activity_kind = models.CharField(max_length=24, choices=ResponseActivityKind.choices)
    details = models.CharField(max_length=2000, null=True, blank=True)
    command_id = models.UUIDField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "responses_response"
        constraints = [
            models.CheckConstraint(
                condition=Q(activity_kind__in=ResponseActivityKind.values),
                name="ck_response_activity_kind",
            ),
            models.UniqueConstraint(
                fields=["command_id"],
                condition=Q(command_id__isnull=False),
                name="uq_response_command",
            ),
        ]
        indexes = [
            models.Index(
                fields=["response_assignment", "occurred_at"], name="ix_response_assignment_time"
            ),
        ]


class AssignmentStatusHistory(AppendOnlyUUIDModel):
    Status = AssignmentStatus

    response_assignment = models.ForeignKey(
        ResponseAssignment,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=24, null=True, blank=True)
    to_status = models.CharField(max_length=24, choices=AssignmentStatus.choices)
    changed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_index=False,
        related_name="assignment_status_changes",
    )
    actor_service_ref = models.CharField(max_length=128, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    command_id = models.UUIDField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "responses_assignment_status_history"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(from_status__isnull=True, to_status=AssignmentStatus.PENDING)
                    | (
                        Q(from_status__in=AssignmentStatus.values)
                        & Q(to_status__in=AssignmentStatus.values)
                        & ~Q(from_status=F("to_status"))
                    )
                ),
                name="ck_assignment_history_transition",
            ),
            models.CheckConstraint(
                condition=(
                    Q(changed_by_user__isnull=False, actor_service_ref__isnull=True)
                    | Q(
                        changed_by_user__isnull=True,
                        actor_service_ref__isnull=False,
                        actor_service_ref__regex=r"\S",
                    )
                ),
                name="ck_assignment_history_actor_xor",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        to_status__in=[
                            AssignmentStatus.UNABLE_TO_RESPOND,
                            AssignmentStatus.CANCELLED,
                            AssignmentStatus.EXPIRED,
                        ],
                        reason__isnull=False,
                        reason__regex=r"\S",
                    )
                    | ~Q(
                        to_status__in=[
                            AssignmentStatus.UNABLE_TO_RESPOND,
                            AssignmentStatus.CANCELLED,
                            AssignmentStatus.EXPIRED,
                        ]
                    )
                ),
                name="ck_assignment_history_reason",
            ),
            models.UniqueConstraint(
                fields=["command_id"],
                condition=Q(command_id__isnull=False),
                name="uq_assignment_history_command",
            ),
        ]
        indexes = [
            models.Index(
                fields=["response_assignment", "occurred_at"], name="ix_assign_history_time"
            ),
            models.Index(fields=["changed_by_user", "occurred_at"], name="ix_assign_actor_time"),
        ]
