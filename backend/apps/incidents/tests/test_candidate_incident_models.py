import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.incidents.models import (
    AccidentCandidate,
    AccidentIncident,
    CandidateDetectionEvent,
    CandidateReview,
    IncidentStatusHistory,
)


@pytest.mark.django_db
def test_detection_event_can_be_associated_with_only_one_candidate(candidate, detection_event):
    CandidateDetectionEvent.objects.create(
        candidate=candidate,
        detection_event=detection_event,
        association_method=CandidateDetectionEvent.Method.RULE_BASED,
    )
    other_candidate = AccidentCandidate.objects.create()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateDetectionEvent.objects.create(
                candidate=other_candidate,
                detection_event=detection_event,
                association_method=CandidateDetectionEvent.Method.RULE_BASED,
            )


@pytest.mark.django_db
def test_manual_candidate_event_association_requires_human_actor(candidate, detection_event):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateDetectionEvent.objects.create(
                candidate=candidate,
                detection_event=detection_event,
                association_method=CandidateDetectionEvent.Method.MANUAL,
            )


@pytest.mark.django_db
def test_rejected_candidate_review_requires_rationale(candidate, user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateReview.objects.create(
                candidate=candidate,
                reviewer=user,
                decision=CandidateReview.Decision.REJECTED,
                rationale="   ",
            )


@pytest.mark.django_db
def test_candidate_has_one_final_review_and_one_authoritative_incident(candidate, user):
    CandidateReview.objects.create(
        candidate=candidate,
        reviewer=user,
        decision=CandidateReview.Decision.VERIFIED,
    )
    AccidentIncident.objects.create(candidate=candidate)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateReview.objects.create(
                candidate=candidate,
                reviewer=user,
                decision=CandidateReview.Decision.REJECTED,
                rationale="Duplicate final decision.",
            )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AccidentIncident.objects.create(candidate=candidate)


@pytest.mark.django_db
def test_incident_status_history_requires_actor_and_resolution_reason(incident, user):
    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status=None,
        to_status=IncidentStatusHistory.Status.OPEN,
        changed_by_user=user,
        occurred_at=timezone.now(),
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IncidentStatusHistory.objects.create(
                incident=incident,
                from_status=IncidentStatusHistory.Status.OPEN,
                to_status=IncidentStatusHistory.Status.CLOSED,
                changed_by_user=user,
                reason="  ",
            )
