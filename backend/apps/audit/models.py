"""Append-oriented cross-domain audit ledger."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Func, Q, Value
from django.db.models.lookups import Exact
from django.utils import timezone

from common.models import AppendOnlyUUIDModel


class AuditEvent(AppendOnlyUUIDModel):
    class ActorKind(models.TextChoices):
        HUMAN = "HUMAN", "Human"
        MACHINE = "MACHINE", "Machine"
        ANONYMOUS = "ANONYMOUS", "Anonymous"

    class ResourceType(models.TextChoices):
        USER = "USER", "User"
        ORGANIZATION = "ORGANIZATION", "Organization"
        MEMBERSHIP = "MEMBERSHIP", "Membership"
        VIDEO_SOURCE = "VIDEO_SOURCE", "Video source"
        DETECTION_EVENT = "DETECTION_EVENT", "Detection event"
        CANDIDATE = "CANDIDATE", "Candidate"
        INCIDENT = "INCIDENT", "Incident"
        ASSIGNMENT = "ASSIGNMENT", "Assignment"
        EVIDENCE = "EVIDENCE", "Evidence"
        LOCATION = "LOCATION", "Location"
        NOTIFICATION = "NOTIFICATION", "Notification"
        AUTHENTICATION = "AUTHENTICATION", "Authentication"

    class Outcome(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        DENIED = "DENIED", "Denied"
        FAILED = "FAILED", "Failed"
        SIMULATED = "SIMULATED", "Simulated"

    actor_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=False,
        related_name="audit_events",
    )
    actor_kind = models.CharField(max_length=12, choices=ActorKind.choices)
    actor_service_ref = models.CharField(max_length=128, null=True, blank=True)
    actor_ref_snapshot = models.CharField(max_length=128)
    resource_type = models.CharField(max_length=32, choices=ResourceType.choices)
    resource_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=80)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    request_id = models.UUIDField(null=True, blank=True, db_index=False)
    context_schema_version = models.PositiveSmallIntegerField(default=1)
    safe_context = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "audit_audit_event"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        actor_kind="HUMAN",
                        actor_service_ref__isnull=True,
                    )
                    | Q(
                        actor_kind="MACHINE",
                        actor_user__isnull=True,
                        actor_service_ref__isnull=False,
                        actor_ref_snapshot=F("actor_service_ref"),
                    )
                    | Q(
                        actor_kind="ANONYMOUS",
                        actor_user__isnull=True,
                        actor_service_ref__isnull=True,
                        actor_ref_snapshot="ANONYMOUS",
                    )
                )
                & ~Q(actor_ref_snapshot__regex=r"^\s*$"),
                name="ck_audit_actor_kind",
            ),
            models.CheckConstraint(
                condition=Q(
                    resource_type__in=[
                        "USER",
                        "ORGANIZATION",
                        "MEMBERSHIP",
                        "VIDEO_SOURCE",
                        "DETECTION_EVENT",
                        "CANDIDATE",
                        "INCIDENT",
                        "ASSIGNMENT",
                        "EVIDENCE",
                        "LOCATION",
                        "NOTIFICATION",
                        "AUTHENTICATION",
                    ]
                ),
                name="ck_audit_target",
            ),
            models.CheckConstraint(
                condition=Q(outcome__in=["SUCCESS", "DENIED", "FAILED", "SIMULATED"]),
                name="ck_audit_outcome",
            ),
            models.CheckConstraint(
                condition=Exact(
                    Func(
                        F("safe_context"),
                        function="jsonb_typeof",
                        output_field=models.CharField(),
                    ),
                    Value("object"),
                ),
                name="ck_audit_context_object",
            ),
            models.CheckConstraint(
                condition=Q(context_schema_version__gte=1),
                name="ck_audit_context_version",
            ),
            models.CheckConstraint(
                condition=Q(action__regex=r"^\S+$"),
                name="ck_audit_action_nonblank",
            ),
        ]
        indexes = [
            models.Index(fields=["occurred_at"], name="ix_audit_occurred"),
            models.Index(fields=["action", "occurred_at"], name="ix_audit_action_time"),
            models.Index(
                fields=["resource_type", "resource_id", "occurred_at"],
                name="ix_audit_resource_time",
            ),
            models.Index(fields=["actor_user", "occurred_at"], name="ix_audit_human_actor_time"),
            models.Index(
                fields=["actor_service_ref", "occurred_at"],
                name="ix_audit_machine_actor_time",
            ),
            models.Index(fields=["request_id"], name="ix_audit_request_id"),
        ]

    def save(self, *args, **kwargs):
        if not isinstance(self.safe_context, dict):
            raise ValidationError({"safe_context": "Audit context must be a JSON object."})
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.action} ({self.occurred_at.isoformat()})"
