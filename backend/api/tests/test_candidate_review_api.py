"""Authenticated API coverage for Police candidate review and decisions."""

from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.incidents.models import (
    AccidentCandidate,
    AccidentIncident,
    CandidateDetectionEvent,
    CandidateReview,
    CandidateReviewerAssignment,
    CandidateStatus,
    IncidentStatus,
    IncidentStatusHistory,
)
from apps.organizations.models import MembershipStatus, Organization, OrganizationMembership


def _client_with_token(user):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/token/",
        {"email": user.email, "password": "local-test-password"},
        format="json",
    )
    assert response.status_code == 200, response.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    return client


def _police_membership(user, organization):
    return OrganizationMembership.objects.create(
        user=user,
        organization=organization,
        role_group=Group.objects.get(name="POLICE"),
        status=MembershipStatus.ACTIVE,
    )


def _assigned_candidate(user, police_organization, detection_event):
    candidate = AccidentCandidate.objects.create(police_organization=police_organization)
    _police_membership(user, police_organization)
    CandidateDetectionEvent.objects.create(
        candidate=candidate,
        detection_event=detection_event,
        association_method=CandidateDetectionEvent.Method.RULE_BASED,
    )
    CandidateReviewerAssignment.objects.create(
        candidate=candidate,
        police_organization=police_organization,
        reviewer=user,
        assigned_by_user=user,
        command_id=uuid4(),
    )
    return candidate


@pytest.mark.django_db
def test_assigned_reviewer_can_start_and_verify_through_authenticated_api(
    user, police_organization, detection_event
):
    candidate = _assigned_candidate(user, police_organization, detection_event)
    client = _client_with_token(user)

    listing = client.get("/api/v1/candidates/")
    detail = client.get(f"/api/v1/candidates/{candidate.pk}/")
    assert listing.status_code == detail.status_code == 200
    assert listing.json()["count"] == 1
    assert listing.json()["results"][0]["id"] == str(candidate.pk)
    assert set(detail.json()) == {
        "id",
        "police_organization_id",
        "status",
        "created_at",
        "updated_at",
    }

    start_command = uuid4()
    started = client.post(
        f"/api/v1/candidates/{candidate.pk}/review/",
        {"command_id": str(start_command)},
        format="json",
    )
    assert started.status_code == 200, started.content
    assert started.json()["data"]["status"] == CandidateStatus.UNDER_REVIEW
    assert started.json()["replayed"] is False
    assert AuditEvent.objects.filter(
        action="CANDIDATE_REVIEW_STARTED",
        resource_id=candidate.pk,
        actor_user=user,
    ).exists()

    decision_command = uuid4()
    request_body = {
        "command_id": str(decision_command),
        "rationale": "Confirmed through the permitted candidate summary.",
    }
    verified = client.post(
        f"/api/v1/candidates/{candidate.pk}/verify/", request_body, format="json"
    )
    replay = client.post(f"/api/v1/candidates/{candidate.pk}/verify/", request_body, format="json")
    assert verified.status_code == replay.status_code == 200
    assert verified.json()["data"]["status"] == IncidentStatus.OPEN
    assert replay.json()["replayed"] is True
    assert replay.json()["data"]["id"] == verified.json()["data"]["id"]

    incident = AccidentIncident.objects.get(candidate=candidate)
    review = CandidateReview.objects.get(candidate=candidate)
    assert incident.status == IncidentStatus.OPEN
    assert review.reviewer_id == user.pk
    assert review.decision == CandidateReview.Decision.VERIFIED
    assert review.command_id == decision_command
    assert review.rationale == request_body["rationale"]
    assert IncidentStatusHistory.objects.get(incident=incident).changed_by_user_id == user.pk
    assert (
        AuditEvent.objects.filter(
            action="CANDIDATE_VERIFIED", resource_id=candidate.pk, actor_user=user
        ).count()
        == 1
    )
    assert AuditEvent.objects.filter(
        action="CANDIDATE_VERIFIED", resource_id=candidate.pk
    ).get().safe_context == {
        "command_id": str(decision_command),
        "incident_id": str(incident.pk),
    }


@pytest.mark.django_db
def test_assigned_reviewer_can_reject_without_an_incident(
    user, police_organization, detection_event
):
    candidate = _assigned_candidate(user, police_organization, detection_event)
    client = _client_with_token(user)
    started = client.post(
        f"/api/v1/candidates/{candidate.pk}/review/",
        {"command_id": str(uuid4())},
        format="json",
    )
    assert started.status_code == 200

    missing_rationale = client.post(
        f"/api/v1/candidates/{candidate.pk}/reject/",
        {"command_id": str(uuid4()), "rationale": "   "},
        format="json",
    )
    assert missing_rationale.status_code == 400
    assert missing_rationale.json()["code"] == "validation_error"
    assert CandidateReview.objects.filter(candidate=candidate).count() == 0

    command_id = uuid4()
    rejected = client.post(
        f"/api/v1/candidates/{candidate.pk}/reject/",
        {
            "command_id": str(command_id),
            "rationale": "The observation does not establish an accident.",
        },
        format="json",
    )
    assert rejected.status_code == 200, rejected.content
    assert rejected.json()["data"]["status"] == CandidateStatus.REJECTED
    assert CandidateReview.objects.get(candidate=candidate).reviewer_id == user.pk
    assert not AccidentIncident.objects.filter(candidate=candidate).exists()
    assert AuditEvent.objects.filter(
        action="CANDIDATE_REJECTED",
        resource_id=candidate.pk,
        actor_user=user,
        safe_context__command_id=str(command_id),
    ).exists()


@pytest.mark.django_db
def test_unassigned_and_cross_organization_users_cannot_read_or_review_candidate(
    user, police_organization, detection_event
):
    candidate = _assigned_candidate(user, police_organization, detection_event)
    other_organization = Organization.objects.create(
        code="other-police",
        display_name="Other Police",
        organization_kind="POLICE",
    )
    other_user = get_user_model().objects.create_user(
        "other-police@example.test", "local-test-password"
    )
    _police_membership(other_user, other_organization)
    client = _client_with_token(other_user)

    assert client.get(f"/api/v1/candidates/{candidate.pk}/").status_code == 404
    for path, body in (
        ("review/", {"command_id": str(uuid4())}),
        ("verify/", {"command_id": str(uuid4())}),
        ("reject/", {"command_id": str(uuid4()), "rationale": "Not permitted."}),
    ):
        response = client.post(f"/api/v1/candidates/{candidate.pk}/{path}", body, format="json")
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    assert CandidateReview.objects.filter(candidate=candidate).count() == 0
    assert not AccidentIncident.objects.filter(candidate=candidate).exists()
    assert (
        AuditEvent.objects.filter(action="DOMAIN_ACTION_DENIED", resource_id=candidate.pk).count()
        == 3
    )


@pytest.mark.django_db
def test_membership_is_rechecked_for_each_review_operation(
    user, police_organization, detection_event
):
    candidate = _assigned_candidate(user, police_organization, detection_event)
    membership = OrganizationMembership.objects.get(user=user, organization=police_organization)
    client = _client_with_token(user)
    assert client.get(f"/api/v1/candidates/{candidate.pk}/").status_code == 200

    membership.status = MembershipStatus.SUSPENDED
    membership.save(update_fields=["status", "updated_at"])
    response = client.post(
        f"/api/v1/candidates/{candidate.pk}/review/",
        {"command_id": str(uuid4())},
        format="json",
    )

    assert response.status_code == 404
    assert CandidateReview.objects.filter(candidate=candidate).count() == 0
    assert candidate.refresh_from_db() is None
    assert candidate.status == CandidateStatus.RECEIVED
    assert AuditEvent.objects.filter(
        action="DOMAIN_ACTION_DENIED", resource_id=candidate.pk
    ).exists()


@pytest.mark.django_db
def test_candidate_organization_binding_must_match_immutable_assignment(
    user, police_organization, detection_event
):
    candidate = _assigned_candidate(user, police_organization, detection_event)
    other_organization = Organization.objects.create(
        code="binding-check-police",
        display_name="Binding Check Police",
        organization_kind="POLICE",
    )
    _police_membership(user, other_organization)
    candidate.police_organization = other_organization
    candidate.save(update_fields=["police_organization", "updated_at"])
    client = _client_with_token(user)

    assert client.get(f"/api/v1/candidates/{candidate.pk}/").status_code == 404
    response = client.post(
        f"/api/v1/candidates/{candidate.pk}/review/",
        {"command_id": str(uuid4())},
        format="json",
    )
    assert response.status_code == 404
    assert CandidateReview.objects.filter(candidate=candidate).count() == 0
    assert AuditEvent.objects.filter(
        action="DOMAIN_ACTION_DENIED", resource_id=candidate.pk
    ).exists()
