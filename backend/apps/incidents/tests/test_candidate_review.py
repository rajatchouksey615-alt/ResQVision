"""Assigned Police review commands and their atomic decision outcomes."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from django.contrib.auth.models import Group
from django.db import close_old_connections, connections

from api.v1.policies import AssignedCandidateReviewPolicy
from apps.audit.models import AuditEvent
from apps.incidents.models import (
    AccidentIncident,
    CandidateDetectionEvent,
    CandidateReview,
    CandidateReviewerAssignment,
    CandidateStatus,
    IncidentStatus,
    IncidentStatusHistory,
)
from apps.incidents.services import begin_candidate_review, reject_candidate, verify_candidate
from apps.organizations.models import MembershipStatus, OrganizationMembership
from common.domain.actors import HumanActor
from common.domain.exceptions import AuthorizationDenied, InvalidStateTransition


def _active_police_membership(user, organization):
    police_group, _ = Group.objects.get_or_create(name="POLICE")
    return OrganizationMembership.objects.create(
        user=user,
        organization=organization,
        role_group=police_group,
        status=MembershipStatus.ACTIVE,
    )


def _assigned_candidate(candidate, detection_event, reviewer, police_organization):
    candidate.police_organization = police_organization
    candidate.save(update_fields=["police_organization", "updated_at"])
    _active_police_membership(reviewer, police_organization)
    CandidateDetectionEvent.objects.create(
        candidate=candidate,
        detection_event=detection_event,
        association_method=CandidateDetectionEvent.Method.RULE_BASED,
    )
    CandidateReviewerAssignment.objects.create(
        candidate=candidate,
        police_organization=police_organization,
        reviewer=reviewer,
        assigned_by_user=reviewer,
        command_id=uuid4(),
    )
    return candidate


@pytest.mark.django_db
def test_assigned_reviewer_starts_and_verifies_candidate_atomically(
    candidate, detection_event, user, police_organization
):
    candidate = _assigned_candidate(candidate, detection_event, user, police_organization)
    actor = HumanActor(user)
    policy = AssignedCandidateReviewPolicy()
    start_id = uuid4()
    decision_id = uuid4()

    started = begin_candidate_review(
        candidate_id=candidate.pk, actor=actor, command_id=start_id, policy=policy
    )
    assert not started.replayed
    assert started.value.status == CandidateStatus.UNDER_REVIEW
    assert AuditEvent.objects.filter(
        action="CANDIDATE_REVIEW_STARTED",
        resource_id=candidate.pk,
        actor_user=user,
        safe_context__command_id=str(start_id),
    ).exists()

    verified = verify_candidate(
        candidate_id=candidate.pk,
        actor=actor,
        command_id=decision_id,
        rationale="Verified from the available event record.",
        policy=policy,
    )
    replay = verify_candidate(
        candidate_id=candidate.pk,
        actor=actor,
        command_id=decision_id,
        rationale="Verified from the available event record.",
        policy=policy,
    )

    assert not verified.replayed
    assert replay.replayed
    assert replay.value.pk == verified.value.pk
    assert replay.value.status == IncidentStatus.OPEN
    assert replay.value.candidate_id == candidate.pk
    assert AccidentIncident.objects.filter(candidate=candidate).count() == 1
    review = CandidateReview.objects.get(candidate=candidate)
    assert review.reviewer_id == user.pk
    assert review.decision == CandidateReview.Decision.VERIFIED
    assert review.rationale == "Verified from the available event record."
    assert review.command_id == decision_id
    history = IncidentStatusHistory.objects.get(incident=verified.value)
    assert history.changed_by_user_id == user.pk
    assert history.to_status == IncidentStatus.OPEN
    assert history.command_id == decision_id
    audit = AuditEvent.objects.get(action="CANDIDATE_VERIFIED", resource_id=candidate.pk)
    assert audit.actor_user_id == user.pk
    assert audit.safe_context == {
        "command_id": str(decision_id),
        "incident_id": str(verified.value.pk),
    }
    assert (
        AuditEvent.objects.filter(action="CANDIDATE_VERIFIED", resource_id=candidate.pk).count()
        == 1
    )


@pytest.mark.django_db
def test_assigned_reviewer_rejects_without_creating_incident(
    candidate, detection_event, user, police_organization
):
    candidate = _assigned_candidate(candidate, detection_event, user, police_organization)
    actor = HumanActor(user)
    policy = AssignedCandidateReviewPolicy()
    begin_candidate_review(
        candidate_id=candidate.pk, actor=actor, command_id=uuid4(), policy=policy
    )
    command_id = uuid4()

    result = reject_candidate(
        candidate_id=candidate.pk,
        actor=actor,
        command_id=command_id,
        rationale="The event does not support an accident finding.",
        policy=policy,
    )

    assert result.value.status == CandidateStatus.REJECTED
    assert CandidateReview.objects.get(candidate=candidate).reviewer_id == user.pk
    assert CandidateReview.objects.get(candidate=candidate).rationale == (
        "The event does not support an accident finding."
    )
    assert not AccidentIncident.objects.filter(candidate=candidate).exists()
    assert AuditEvent.objects.filter(
        action="CANDIDATE_REJECTED",
        resource_id=candidate.pk,
        actor_user=user,
        safe_context__command_id=str(command_id),
    ).exists()


@pytest.mark.django_db
def test_review_policy_rejects_unassigned_inactive_and_cross_organization_users(
    candidate, detection_event, user, police_organization
):
    candidate = _assigned_candidate(candidate, detection_event, user, police_organization)
    policy = AssignedCandidateReviewPolicy()

    unassigned = type(user).objects.create_user("unassigned@example.test", "local-test-password")
    unassigned_membership = _active_police_membership(unassigned, police_organization)
    assert not policy.authorize("candidate.review", HumanActor(unassigned), candidate)

    other_organization_user = type(user).objects.create_user(
        "other-organization@example.test", "local-test-password"
    )
    from apps.organizations.models import Organization

    other_organization = Organization.objects.create(
        code="another-police",
        display_name="Another Police",
        organization_kind="POLICE",
    )
    _active_police_membership(other_organization_user, other_organization)
    assert not policy.authorize("candidate.verify", HumanActor(other_organization_user), candidate)

    unassigned_membership.status = MembershipStatus.SUSPENDED
    unassigned_membership.save(update_fields=["status", "updated_at"])

    user.is_active = False
    user.save(update_fields=["is_active"])
    assert not policy.authorize("candidate.review", HumanActor(user), candidate)


@pytest.mark.django_db
def test_final_decision_requires_review_state(
    candidate, detection_event, user, police_organization
):
    candidate = _assigned_candidate(candidate, detection_event, user, police_organization)

    with pytest.raises(InvalidStateTransition):
        verify_candidate(
            candidate_id=candidate.pk,
            actor=HumanActor(user),
            command_id=uuid4(),
            policy=AssignedCandidateReviewPolicy(),
        )

    assert CandidateReview.objects.filter(candidate=candidate).count() == 0
    assert AccidentIncident.objects.filter(candidate=candidate).count() == 0


@pytest.mark.django_db
def test_inactive_assigned_reviewer_cannot_start_review(
    candidate, detection_event, user, police_organization
):
    candidate = _assigned_candidate(candidate, detection_event, user, police_organization)
    user.is_active = False
    user.save(update_fields=["is_active"])

    with pytest.raises(AuthorizationDenied):
        begin_candidate_review(
            candidate_id=candidate.pk,
            actor=HumanActor(user),
            command_id=uuid4(),
            policy=AssignedCandidateReviewPolicy(),
        )

    candidate.refresh_from_db()
    assert candidate.status == CandidateStatus.RECEIVED
    assert CandidateReview.objects.filter(candidate=candidate).count() == 0
    assert AuditEvent.objects.filter(
        action="DOMAIN_ACTION_DENIED", resource_id=candidate.pk
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_command_verification_creates_one_incident(
    candidate, detection_event, user, police_organization
):
    candidate = _assigned_candidate(candidate, detection_event, user, police_organization)
    actor = HumanActor(user)
    policy = AssignedCandidateReviewPolicy()
    begin_candidate_review(
        candidate_id=candidate.pk, actor=actor, command_id=uuid4(), policy=policy
    )
    command_id = uuid4()
    rendezvous = Barrier(2)

    def attempt():
        close_old_connections()
        try:
            rendezvous.wait(timeout=10)
            result = verify_candidate(
                candidate_id=candidate.pk,
                actor=actor,
                command_id=command_id,
                policy=policy,
            )
            return result.value.pk, result.replayed
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))

    assert len({incident_id for incident_id, _ in results}) == 1
    assert sorted(replayed for _, replayed in results) == [False, True]
    assert (
        AccidentIncident.objects.filter(candidate=candidate, status=IncidentStatus.OPEN).count()
        == 1
    )
    assert CandidateReview.objects.filter(candidate=candidate).count() == 1
    assert (
        AuditEvent.objects.filter(action="CANDIDATE_VERIFIED", resource_id=candidate.pk).count()
        == 1
    )
