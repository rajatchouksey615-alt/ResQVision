"""Human-reviewed accident candidates, authoritative incidents, and histories."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.detection.models import DetectionEvent
from apps.organizations.models import Organization
from common.models import AppendOnlyUUIDModel, UUIDPrimaryKeyModel


class CandidateStatus(models.TextChoices):
    RECEIVED = "RECEIVED", "Received"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class AssociationMethod(models.TextChoices):
    RULE_BASED = "RULE_BASED", "Rule based"
    REVIEWER_CONFIRMED = "REVIEWER_CONFIRMED", "Reviewer confirmed"
    MANUAL = "MANUAL", "Manual"


class ReviewDecision(models.TextChoices):
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class IncidentStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    RESPONSE_ACTIVE = "RESPONSE_ACTIVE", "Response active"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class AccidentCandidate(UUIDPrimaryKeyModel):
    Status = CandidateStatus

    police_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accident_candidates",
    )
    status = models.CharField(
        max_length=20,
        choices=CandidateStatus.choices,
        default=CandidateStatus.RECEIVED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "incidents_accident_candidate"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=CandidateStatus.values),
                name="ck_candidate_status",
            )
        ]
        indexes = [models.Index(fields=["status", "created_at"], name="ix_candidate_review_queue")]

    def __str__(self) -> str:
        return f"Candidate {self.pk} ({self.status})"


class CandidateDetectionEvent(UUIDPrimaryKeyModel):
    Method = AssociationMethod

    candidate = models.ForeignKey(
        AccidentCandidate,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="detection_links",
    )
    detection_event = models.ForeignKey(
        DetectionEvent,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="candidate_link",
    )
    association_method = models.CharField(max_length=20, choices=AssociationMethod.choices)
    linked_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="candidate_event_links",
    )
    linked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "incidents_candidate_detection_event"
        constraints = [
            models.UniqueConstraint(
                fields=["detection_event"],
                name="uq_candidate_event_once",
            ),
            models.CheckConstraint(
                condition=(
                    Q(association_method__in=AssociationMethod.values)
                    & (
                        Q(
                            association_method=AssociationMethod.RULE_BASED,
                            linked_by_user__isnull=True,
                        )
                        | Q(
                            association_method__in=[
                                AssociationMethod.REVIEWER_CONFIRMED,
                                AssociationMethod.MANUAL,
                            ],
                            linked_by_user__isnull=False,
                        )
                    )
                ),
                name="ck_association_method",
            ),
        ]
        indexes = [
            models.Index(fields=["candidate", "linked_at"], name="ix_cand_event_candidate_time")
        ]


class CandidateReview(AppendOnlyUUIDModel):
    Decision = ReviewDecision

    candidate = models.ForeignKey(
        AccidentCandidate,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="final_review",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="candidate_reviews",
    )
    decision = models.CharField(max_length=12, choices=ReviewDecision.choices)
    rationale = models.TextField(null=True, blank=True)
    reviewed_at = models.DateTimeField(default=timezone.now)
    command_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "incidents_candidate_review"
        constraints = [
            models.UniqueConstraint(fields=["candidate"], name="uq_review_candidate_final"),
            models.UniqueConstraint(
                fields=["command_id"],
                condition=Q(command_id__isnull=False),
                name="uq_review_command",
            ),
            models.CheckConstraint(
                condition=(
                    Q(decision__in=ReviewDecision.values)
                    & (
                        ~Q(decision=ReviewDecision.REJECTED)
                        | Q(rationale__isnull=False, rationale__regex=r"\S")
                    )
                ),
                name="ck_review_rationale",
            ),
        ]
        indexes = [
            models.Index(fields=["reviewer", "reviewed_at"], name="ix_review_reviewer_time"),
            models.Index(fields=["reviewed_at"], name="ix_review_time"),
        ]


class AccidentIncident(UUIDPrimaryKeyModel):
    Status = IncidentStatus

    candidate = models.ForeignKey(
        AccidentCandidate,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="incident",
    )
    status = models.CharField(
        max_length=20,
        choices=IncidentStatus.choices,
        default=IncidentStatus.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "incidents_accident_incident"
        constraints = [
            models.UniqueConstraint(fields=["candidate"], name="uq_incident_candidate"),
            models.CheckConstraint(
                condition=Q(status__in=IncidentStatus.values),
                name="ck_incident_status",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="ix_incident_status_created"),
            models.Index(fields=["created_at"], name="ix_incident_created"),
        ]

    def __str__(self) -> str:
        return f"Incident {self.pk} ({self.status})"


class IncidentStatusHistory(AppendOnlyUUIDModel):
    Status = IncidentStatus

    incident = models.ForeignKey(
        AccidentIncident,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20, choices=IncidentStatus.choices)
    changed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_index=False,
        related_name="incident_status_changes",
    )
    actor_service_ref = models.CharField(max_length=128, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    command_id = models.UUIDField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "incidents_incident_status_history"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(from_status__isnull=True, to_status=IncidentStatus.OPEN)
                    | (
                        Q(from_status__in=IncidentStatus.values)
                        & Q(to_status__in=IncidentStatus.values)
                        & ~Q(from_status=F("to_status"))
                    )
                ),
                name="ck_incident_history_transition",
            ),
            models.CheckConstraint(
                condition=(
                    Q(changed_by_user__isnull=False, actor_service_ref__isnull=True)
                    | (
                        Q(changed_by_user__isnull=True)
                        & Q(actor_service_ref__isnull=False)
                        & Q(actor_service_ref__regex=r"\S")
                    )
                ),
                name="ck_history_actor_xor",
            ),
            models.CheckConstraint(
                condition=(
                    Q(to_status__in=[IncidentStatus.OPEN, IncidentStatus.RESPONSE_ACTIVE])
                    | (
                        Q(to_status__in=[IncidentStatus.RESOLVED, IncidentStatus.CLOSED])
                        & Q(reason__isnull=False)
                        & Q(reason__regex=r"\S")
                    )
                ),
                name="ck_incident_history_reason",
            ),
            models.UniqueConstraint(
                fields=["command_id"],
                condition=Q(command_id__isnull=False),
                name="uq_history_command_incident",
            ),
        ]
        indexes = [
            models.Index(fields=["incident", "occurred_at"], name="ix_incident_history_time"),
            models.Index(fields=["changed_by_user", "occurred_at"], name="ix_incident_actor_time"),
        ]
