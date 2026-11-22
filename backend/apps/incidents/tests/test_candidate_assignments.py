"""Police reviewer assignment scope, history, idempotency, and concurrency."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections

from apps.audit.models import AuditEvent
from apps.incidents.models import AccidentCandidate, CandidateReviewerAssignment
from apps.incidents.services import assign_candidate_reviewer
from apps.organizations.models import MembershipStatus, Organization, OrganizationMembership
from common.domain.actors import HumanActor
from common.domain.exceptions import (
    AuthorizationDenied,
    BusinessRuleViolation,
    ResourceConflict,
)


def add_police_membership(user, organization):
    return OrganizationMembership.objects.create(
        user=user,
        organization=organization,
        role_group=Group.objects.get(name="POLICE"),
        status=MembershipStatus.ACTIVE,
    )


def make_assigner(organization, email="admin@example.test"):
    user = get_user_model().objects.create_user(email, "local-test-password")
    user.groups.add(Group.objects.get(name="ADMIN"))
    add_police_membership(user, organization)
    return user


def bind_candidate(candidate, organization):
    candidate.police_organization = organization
    candidate.save(update_fields=["police_organization", "updated_at"])
    return candidate


@pytest.mark.django_db
def test_authorized_assignment_is_append_only_and_audited(candidate, user, police_organization):
    candidate = bind_candidate(candidate, police_organization)
    assigner = make_assigner(police_organization)
    add_police_membership(user, police_organization)
    command_id = uuid4()

    result = assign_candidate_reviewer(
        candidate_id=candidate.pk,
        reviewer_id=user.pk,
        actor=HumanActor(assigner),
        command_id=command_id,
    )

    assignment = result.value
    assert not result.replayed
    assert assignment.candidate_id == candidate.pk
    assert assignment.police_organization_id == police_organization.pk
    assert assignment.reviewer_id == user.pk
    assert assignment.assigned_by_user_id == assigner.pk
    audit = AuditEvent.objects.get(action="CANDIDATE_REVIEWER_ASSIGNED", resource_id=candidate.pk)
    assert audit.actor_user_id == assigner.pk
    assert audit.safe_context == {
        "assignment_id": str(assignment.pk),
        "candidate_id": str(candidate.pk),
        "organization_id": str(police_organization.pk),
        "reviewer_id": str(user.pk),
        "command_id": str(command_id),
    }
    with pytest.raises(ValidationError, match="append-only"):
        assignment.delete()
    with pytest.raises(ValidationError, match="append-only"):
        CandidateReviewerAssignment.objects.filter(pk=assignment.pk).update(reviewer=user)


@pytest.mark.django_db
def test_assigner_needs_admin_group_and_active_membership(candidate, user, police_organization):
    candidate = bind_candidate(candidate, police_organization)
    add_police_membership(user, police_organization)
    other_reviewer = get_user_model().objects.create_user(
        "other-reviewer@example.test", "local-test-password"
    )
    add_police_membership(other_reviewer, police_organization)

    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    with pytest.raises(AuthorizationDenied):
        assign_candidate_reviewer(
            candidate_id=candidate.pk,
            reviewer_id=other_reviewer.pk,
            actor=HumanActor(user),
            command_id=uuid4(),
        )

    user.is_superuser = False
    user.save(update_fields=["is_superuser"])
    user.groups.add(Group.objects.get(name="ADMIN"))
    membership = OrganizationMembership.objects.get(user=user, organization=police_organization)
    membership.status = MembershipStatus.SUSPENDED
    membership.save(update_fields=["status", "updated_at"])
    with pytest.raises(AuthorizationDenied):
        assign_candidate_reviewer(
            candidate_id=candidate.pk,
            reviewer_id=other_reviewer.pk,
            actor=HumanActor(user),
            command_id=uuid4(),
        )

    assert not CandidateReviewerAssignment.objects.filter(candidate=candidate).exists()
    assert (
        AuditEvent.objects.filter(action="DOMAIN_ACTION_DENIED", resource_id=candidate.pk).count()
        == 2
    )


@pytest.mark.django_db
def test_inactive_or_cross_organization_reviewer_is_rejected(candidate, user, police_organization):
    candidate = bind_candidate(candidate, police_organization)
    assigner = make_assigner(police_organization)
    inactive = get_user_model().objects.create_user(
        "inactive-reviewer@example.test", "local-test-password"
    )
    add_police_membership(inactive, police_organization)
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])

    with pytest.raises(AuthorizationDenied):
        assign_candidate_reviewer(
            candidate_id=candidate.pk,
            reviewer_id=inactive.pk,
            actor=HumanActor(assigner),
            command_id=uuid4(),
        )

    other_organization = Organization.objects.create(
        code="north-police",
        display_name="North Police",
        organization_kind=Organization.Kind.POLICE,
    )
    add_police_membership(user, other_organization)
    with pytest.raises(AuthorizationDenied):
        assign_candidate_reviewer(
            candidate_id=candidate.pk,
            reviewer_id=user.pk,
            actor=HumanActor(assigner),
            command_id=uuid4(),
        )

    suspended = get_user_model().objects.create_user(
        "suspended-reviewer@example.test", "local-test-password"
    )
    membership = add_police_membership(suspended, police_organization)
    membership.status = MembershipStatus.SUSPENDED
    membership.save(update_fields=["status", "updated_at"])
    with pytest.raises(AuthorizationDenied):
        assign_candidate_reviewer(
            candidate_id=candidate.pk,
            reviewer_id=suspended.pk,
            actor=HumanActor(assigner),
            command_id=uuid4(),
        )

    assert not CandidateReviewerAssignment.objects.filter(candidate=candidate).exists()


@pytest.mark.django_db
def test_candidate_without_valid_police_organization_cannot_be_assigned(
    user, police_organization, hospital_organization
):
    candidate = AccidentCandidate.objects.create()
    assigner = make_assigner(police_organization)
    add_police_membership(user, police_organization)

    invalid_orgs = [None, hospital_organization]
    inactive_police = Organization.objects.create(
        code="inactive-police",
        display_name="Inactive Police",
        organization_kind=Organization.Kind.POLICE,
        is_active=False,
    )
    invalid_orgs.append(inactive_police)
    for organization in invalid_orgs:
        candidate.police_organization = organization
        candidate.save(update_fields=["police_organization", "updated_at"])
        with pytest.raises(BusinessRuleViolation, match="valid Police organization"):
            assign_candidate_reviewer(
                candidate_id=candidate.pk,
                reviewer_id=user.pk,
                actor=HumanActor(assigner),
                command_id=uuid4(),
            )

    assert not CandidateReviewerAssignment.objects.filter(candidate=candidate).exists()


@pytest.mark.django_db
def test_duplicate_assignment_is_prevented_and_same_command_replays(
    candidate, user, police_organization
):
    candidate = bind_candidate(candidate, police_organization)
    assigner = make_assigner(police_organization)
    add_police_membership(user, police_organization)
    command_id = uuid4()
    first = assign_candidate_reviewer(
        candidate_id=candidate.pk,
        reviewer_id=user.pk,
        actor=HumanActor(assigner),
        command_id=command_id,
    )
    replay = assign_candidate_reviewer(
        candidate_id=candidate.pk,
        reviewer_id=user.pk,
        actor=HumanActor(assigner),
        command_id=command_id,
    )

    assert replay.replayed
    assert replay.value.pk == first.value.pk
    with pytest.raises(ResourceConflict):
        assign_candidate_reviewer(
            candidate_id=candidate.pk,
            reviewer_id=user.pk,
            actor=HumanActor(assigner),
            command_id=uuid4(),
        )
    assert CandidateReviewerAssignment.objects.filter(candidate=candidate).count() == 1
    assert (
        AuditEvent.objects.filter(
            action="CANDIDATE_REVIEWER_ASSIGNED", resource_id=candidate.pk
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_assignments_create_one_record(candidate, user, police_organization):
    candidate = bind_candidate(candidate, police_organization)
    reviewer = get_user_model().objects.create_user("target@example.test", "test-password")
    add_police_membership(reviewer, police_organization)
    assigners = [
        make_assigner(police_organization, "admin-one@example.test"),
        make_assigner(police_organization, "admin-two@example.test"),
    ]
    rendezvous = Barrier(2)

    def attempt(assigner):
        close_old_connections()
        try:
            rendezvous.wait(timeout=10)
            try:
                assign_candidate_reviewer(
                    candidate_id=candidate.pk,
                    reviewer_id=reviewer.pk,
                    actor=HumanActor(assigner),
                    command_id=uuid4(),
                )
                return "assigned"
            except ResourceConflict:
                return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, assigners))

    assert sorted(results) == ["assigned", "conflict"]
    assert CandidateReviewerAssignment.objects.filter(candidate=candidate).count() == 1
