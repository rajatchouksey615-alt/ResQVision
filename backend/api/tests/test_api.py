"""PostgreSQL-backed API authentication, authorization, and integration tests."""

from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import UntypedToken

from apps.audit.models import AuditEvent
from apps.detection.models import DetectionEvent
from apps.incidents.models import (
    AccidentCandidate,
    AccidentIncident,
    CandidateReviewerAssignment,
)
from apps.notifications.models import Notification, NotificationStatus
from apps.organizations.models import MembershipStatus, Organization, OrganizationMembership
from apps.responses.models import AssignmentStatus, AssignmentStatusHistory, Response
from apps.responses.services import create_assignment
from apps.sources.models import VideoSourceAuthorizationStatus
from common.domain.actors import HumanActor


class AllowPolicy:
    def __init__(self, *operations):
        self.operations = frozenset(operations)

    def authorize(self, operation, actor, resource=None):
        del actor, resource
        return operation in self.operations


def make_client_with_token(user, password="local-test-password"):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/token/",
        {"email": user.email.upper(), "password": password},
        format="json",
    )
    assert response.status_code == 200, response.content
    token = response.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client, response.json()


def add_membership(user, organization):
    return OrganizationMembership.objects.create(
        user=user,
        organization=organization,
        role_group=Group.objects.get(name=organization.organization_kind),
        status=MembershipStatus.ACTIVE,
    )


def make_assignment(incident, organization, actor):
    return create_assignment(
        incident_id=incident.pk,
        target_organization_id=organization.pk,
        actor=HumanActor(actor),
        command_id=uuid4(),
        policy=AllowPolicy("assignment.create"),
    ).value


@pytest.mark.django_db
def test_email_login_normalizes_case_and_returns_short_lived_jwt_pair(user):
    response = APIClient().post(
        "/api/v1/auth/token/",
        {"email": user.email.upper(), "password": "local-test-password"},
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"access", "refresh"}
    claims = UntypedToken(payload["access"])
    assert claims["user_id"] == str(user.pk)
    assert claims["token_type"] == "access"
    assert "roles" not in claims
    assert "email" not in claims
    assert response["X-Request-ID"]


@pytest.mark.django_db
def test_failed_login_uses_same_safe_error_for_unknown_and_wrong_password(user):
    client = APIClient()
    known = client.post(
        "/api/v1/auth/token/",
        {"email": user.email, "password": "wrong-password"},
        format="json",
    )
    unknown = client.post(
        "/api/v1/auth/token/",
        {"email": "nobody@example.test", "password": "wrong-password"},
        format="json",
    )

    assert known.status_code == unknown.status_code == 401
    assert (known.json()["code"], known.json()["detail"]) == (
        unknown.json()["code"],
        unknown.json()["detail"],
    )
    assert "nobody" not in str(unknown.json()).lower()


@pytest.mark.django_db
def test_inactive_account_cannot_login(user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = APIClient().post(
        "/api/v1/auth/token/",
        {"email": user.email, "password": "local-test-password"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


@pytest.mark.django_db
def test_refresh_rotation_blacklists_previous_token_and_refresh_cannot_call_protected_api(user):
    client, pair = make_client_with_token(user)
    refresh_only = APIClient()
    protected = APIClient()
    protected.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['refresh']}")
    assert protected.get("/api/v1/auth/me/").status_code == 401

    rotated = refresh_only.post(
        "/api/v1/auth/token/refresh/", {"refresh": pair["refresh"]}, format="json"
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh"] != pair["refresh"]
    assert rotated.json()["access"]
    old_jti = UntypedToken(pair["refresh"])["jti"]
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

    assert BlacklistedToken.objects.filter(token__jti=old_jti).exists()
    assert (
        refresh_only.post(
            "/api/v1/auth/token/refresh/", {"refresh": pair["refresh"]}, format="json"
        ).status_code
        == 401
    )
    assert client.get("/api/v1/auth/me/").status_code == 200


@pytest.mark.django_db
def test_logout_blacklists_own_refresh_idempotently_and_cannot_blacklist_another_users_token(user):
    other = get_user_model().objects.create_user("other@example.test", "other-test-password")
    client_a, pair_a = make_client_with_token(user)
    _, pair_b = make_client_with_token(other, "other-test-password")

    first = client_a.post("/api/v1/auth/logout/", {"refresh": pair_a["refresh"]}, format="json")
    repeated = client_a.post("/api/v1/auth/logout/", {"refresh": pair_a["refresh"]}, format="json")
    other_user = client_a.post(
        "/api/v1/auth/logout/", {"refresh": pair_b["refresh"]}, format="json"
    )

    assert first.status_code == repeated.status_code == 204
    assert other_user.status_code == 403
    assert client_a.get("/api/v1/auth/me/").status_code == 200
    assert (
        APIClient()
        .post("/api/v1/auth/token/refresh/", {"refresh": pair_b["refresh"]}, format="json")
        .status_code
        == 200
    )
    assert pair_a["access"] not in first.content.decode("utf-8")


@pytest.mark.django_db
def test_password_change_revokes_old_access_and_refresh_tokens(user):
    client, pair = make_client_with_token(user)
    response = client.post(
        "/api/v1/auth/password/change/",
        {"current_password": "local-test-password", "new_password": "New-Strong-Password-2026!"},
        format="json",
    )

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me/").status_code == 401
    assert (
        APIClient()
        .post("/api/v1/auth/token/refresh/", {"refresh": pair["refresh"]}, format="json")
        .status_code
        == 401
    )
    login = APIClient().post(
        "/api/v1/auth/token/",
        {"email": user.email, "password": "New-Strong-Password-2026!"},
        format="json",
    )
    assert login.status_code == 200


@pytest.mark.django_db
def test_account_profile_only_updates_self_editable_fields_and_me_lists_live_memberships(
    user, police_organization
):
    add_membership(user, police_organization)
    client, _ = make_client_with_token(user)

    patched = client.patch("/api/v1/accounts/me/", {"first_name": "Rajat"}, format="json")
    profile = client.get("/api/v1/accounts/me/")
    current = client.get("/api/v1/auth/me/")
    own_memberships = client.get("/api/v1/organizations/me/")
    disallowed = client.patch(
        "/api/v1/accounts/me/", {"email": "changed@example.test"}, format="json"
    )

    assert patched.status_code == 200
    assert profile.json()["first_name"] == "Rajat"
    assert profile.json()["email"] == user.email
    assert current.json()["roles"] == []
    assert current.json()["memberships"][0]["organization_id"] == str(police_organization.pk)
    assert own_memberships.json()["count"] == 1
    assert disallowed.status_code == 400
    user.refresh_from_db()
    assert user.email == "reviewer@example.test"


@pytest.mark.django_db
def test_incident_reads_are_limited_to_active_assignment_scope_even_for_admin_group(
    user, incident, police_organization, candidate
):
    add_membership(user, police_organization)
    assignment = make_assignment(incident, police_organization, user)
    unrelated_candidate = AccidentCandidate.objects.create()
    unrelated_incident = AccidentIncident.objects.create(candidate=unrelated_candidate)
    Group.objects.get(name="ADMIN")
    user.groups.add(Group.objects.get(name="ADMIN"))
    client, _ = make_client_with_token(user)

    listed = client.get("/api/v1/incidents/")
    detail = client.get(f"/api/v1/incidents/{incident.pk}/")
    out_of_scope = client.get(f"/api/v1/incidents/{unrelated_incident.pk}/")
    out_of_scope_assignments = client.get(f"/api/v1/incidents/{unrelated_incident.pk}/assignments/")
    visible_assignments = client.get(f"/api/v1/incidents/{incident.pk}/assignments/")
    assignment_detail = client.get(f"/api/v1/assignments/{assignment.pk}/")

    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()["results"]] == [str(incident.pk)]
    assert detail.status_code == assignment_detail.status_code == 200
    assert out_of_scope.status_code == out_of_scope_assignments.status_code == 404
    assert visible_assignments.json()["count"] == 1


@pytest.mark.django_db
def test_assignment_commands_use_domain_service_and_idempotency(
    user, incident, police_organization
):
    add_membership(user, police_organization)
    assignment = make_assignment(incident, police_organization, user)
    client, _ = make_client_with_token(user)
    command_id = str(uuid4())

    first = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": command_id},
        format="json",
    )
    replay = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": command_id},
        format="json",
    )

    assignment.refresh_from_db()
    assert first.status_code == replay.status_code == 200
    assert first.json()["data"]["status"] == AssignmentStatus.ACKNOWLEDGED
    assert replay.json()["replayed"] is True
    assert AuditEvent.objects.filter(
        action="ASSIGNMENT_ACKNOWLEDGED", resource_id=assignment.pk
    ).exists()


@pytest.mark.django_db
def test_assignment_detail_and_actions_hide_other_organization_resources(
    user, incident, hospital_organization
):
    assignment = make_assignment(incident, hospital_organization, user)
    client, _ = make_client_with_token(user)

    detail = client.get(f"/api/v1/assignments/{assignment.pk}/")
    action = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": str(uuid4())},
        format="json",
    )

    assignment.refresh_from_db()
    assert detail.status_code == action.status_code == 404
    assert assignment.status == AssignmentStatus.PENDING


@pytest.mark.django_db
def test_hospital_response_activity_fails_closed_until_policy_is_approved(
    user, incident, hospital_organization
):
    add_membership(user, hospital_organization)
    assignment = make_assignment(incident, hospital_organization, user)
    client, _ = make_client_with_token(user)
    ack = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": str(uuid4())},
        format="json",
    )
    activity = client.post(
        f"/api/v1/assignments/{assignment.pk}/activities/",
        {
            "command_id": str(uuid4()),
            "activity_kind": "READINESS_UPDATE",
            "details": "Simulated readiness update.",
        },
        format="json",
    )
    wrong_kind = client.post(
        f"/api/v1/assignments/{assignment.pk}/activities/",
        {"command_id": str(uuid4()), "activity_kind": "PROGRESS_UPDATE"},
        format="json",
    )

    assert ack.status_code == activity.status_code == wrong_kind.status_code == 503
    assert ack.json()["code"] == activity.json()["code"] == "policy_unavailable"
    assert Response.objects.filter(response_assignment=assignment).count() == 0


@pytest.mark.django_db
def test_hospital_assignment_reads_are_scoped_and_updates_fail_closed(
    user, incident, hospital_organization
):
    add_membership(user, hospital_organization)
    assignment = make_assignment(incident, hospital_organization, user)
    client, _ = make_client_with_token(user)

    incident_list = client.get("/api/v1/incidents/")
    incident_detail = client.get(f"/api/v1/incidents/{incident.pk}/")
    assignment_list = client.get(f"/api/v1/incidents/{incident.pk}/assignments/")
    assignment_detail = client.get(f"/api/v1/assignments/{assignment.pk}/")
    invalid_start = client.post(
        f"/api/v1/assignments/{assignment.pk}/start/",
        {"command_id": str(uuid4()), "details": "Readiness update."},
        format="json",
    )
    acknowledge_command = str(uuid4())
    acknowledged = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": acknowledge_command},
        format="json",
    )
    replay = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": acknowledge_command},
        format="json",
    )
    start_command = uuid4()
    started = client.post(
        f"/api/v1/assignments/{assignment.pk}/start/",
        {"command_id": str(start_command), "details": "Readiness confirmed."},
        format="json",
    )
    complete_command = uuid4()
    completed = client.post(
        f"/api/v1/assignments/{assignment.pk}/complete/",
        {"command_id": str(complete_command), "details": "Simulation complete."},
        format="json",
    )
    unable = client.post(
        f"/api/v1/assignments/{assignment.pk}/unable-to-respond/",
        {"command_id": str(uuid4()), "reason": "No simulated coverage."},
        format="json",
    )

    assert incident_list.status_code == incident_detail.status_code == 200
    assert incident_list.json()["results"][0]["id"] == str(incident.pk)
    assert assignment_list.status_code == assignment_detail.status_code == 200
    assert assignment_list.json()["results"][0]["target_organization_kind"] == "HOSPITAL"
    assert assignment_detail.json()["id"] == str(assignment.pk)
    for response in (invalid_start, acknowledged, replay, started, completed, unable):
        assert response.status_code == 503
        assert response.json()["code"] == "policy_unavailable"

    histories = list(
        AssignmentStatusHistory.objects.filter(response_assignment=assignment).order_by(
            "occurred_at", "pk"
        )
    )
    assert [history.to_status for history in histories] == [AssignmentStatus.PENDING]
    assert all(history.changed_by_user_id == user.pk for history in histories)
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.PENDING
    assert AuditEvent.objects.filter(
        action="DOMAIN_ACTION_DENIED",
        actor_user=user,
        resource_id=assignment.pk,
        outcome=AuditEvent.Outcome.DENIED,
    ).exists()


@pytest.mark.django_db
def test_hospital_unable_to_respond_fails_closed_until_lifecycle_is_approved(
    user, incident, hospital_organization
):
    add_membership(user, hospital_organization)
    assignment = make_assignment(incident, hospital_organization, user)
    client, _ = make_client_with_token(user)
    response = client.post(
        f"/api/v1/assignments/{assignment.pk}/unable-to-respond/",
        {"command_id": str(uuid4()), "reason": "No simulated coverage."},
        format="json",
    )

    assert response.status_code == 503
    assert response.json()["code"] == "policy_unavailable"
    assert not AssignmentStatusHistory.objects.filter(
        response_assignment=assignment,
        to_status=AssignmentStatus.UNABLE_TO_RESPOND,
    ).exists()
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.PENDING


@pytest.mark.django_db
def test_hospital_assignment_reads_and_updates_require_active_matching_membership(
    user, incident, hospital_organization
):
    assignment = make_assignment(incident, hospital_organization, user)
    assigned_membership = add_membership(user, hospital_organization)
    assigned_membership.status = MembershipStatus.SUSPENDED
    assigned_membership.save(update_fields=["status", "updated_at"])
    other_hospital = Organization.objects.create(
        code="other-hospital",
        display_name="Other Hospital",
        organization_kind="HOSPITAL",
    )
    add_membership(user, other_hospital)
    client, _ = make_client_with_token(user)

    assert client.get("/api/v1/incidents/").json()["count"] == 0
    assert client.get(f"/api/v1/incidents/{incident.pk}/").status_code == 404
    assert client.get(f"/api/v1/assignments/{assignment.pk}/").status_code == 404
    assert client.get(f"/api/v1/incidents/{incident.pk}/assignments/").status_code == 404
    denied = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": str(uuid4())},
        format="json",
    )
    assert denied.status_code == 404
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.PENDING


@pytest.mark.django_db
def test_hospital_assignment_is_hidden_when_target_organization_becomes_inactive(
    user, incident, hospital_organization
):
    add_membership(user, hospital_organization)
    assignment = make_assignment(incident, hospital_organization, user)
    hospital_organization.is_active = False
    hospital_organization.save(update_fields=["is_active", "updated_at"])
    client, _ = make_client_with_token(user)

    assert client.get("/api/v1/incidents/").json()["count"] == 0
    assert client.get(f"/api/v1/incidents/{incident.pk}/").status_code == 404
    assert client.get(f"/api/v1/assignments/{assignment.pk}/").status_code == 404
    assert client.get(f"/api/v1/incidents/{incident.pk}/assignments/").status_code == 404
    denied = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": str(uuid4())},
        format="json",
    )

    assignment.refresh_from_db()
    assert denied.status_code == 404
    assert assignment.status == AssignmentStatus.PENDING


@pytest.mark.django_db
def test_staff_and_superuser_flags_do_not_bypass_hospital_assignment_scope(
    user, incident, hospital_organization
):
    assignment = make_assignment(incident, hospital_organization, user)
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    client, _ = make_client_with_token(user)

    assert client.get("/api/v1/incidents/").json()["count"] == 0
    assert client.get(f"/api/v1/assignments/{assignment.pk}/").status_code == 404
    denied = client.post(
        f"/api/v1/assignments/{assignment.pk}/acknowledge/",
        {"command_id": str(uuid4())},
        format="json",
    )
    assert denied.status_code == 404
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.PENDING


@pytest.mark.django_db
def test_notifications_are_recipient_scoped_and_mark_read_through_domain_service(user, incident):
    other = get_user_model().objects.create_user("notice-other@example.test", "other-pass")
    own = Notification.objects.create(
        recipient_user=user,
        incident=incident,
        status=NotificationStatus.DELIVERED_SIMULATED,
        safe_message_code="INCIDENT_CREATED",
    )
    Notification.objects.create(
        recipient_user=other,
        incident=incident,
        status=NotificationStatus.DELIVERED_SIMULATED,
        safe_message_code="INCIDENT_CREATED",
    )
    client, _ = make_client_with_token(user)

    listing = client.get("/api/v1/notifications/")
    read = client.post(
        f"/api/v1/notifications/{own.pk}/read/",
        {"command_id": str(uuid4())},
        format="json",
    )
    hidden = Notification.objects.filter(recipient_user=other).first()
    hidden_read = client.post(
        f"/api/v1/notifications/{hidden.pk}/read/",
        {"command_id": str(uuid4())},
        format="json",
    )

    assert listing.json()["count"] == 1
    assert listing.json()["results"][0]["id"] == str(own.pk)
    assert read.status_code == 200
    assert read.json()["data"]["status"] == NotificationStatus.READ
    assert hidden_read.status_code == 404
    assert AuditEvent.objects.filter(action="NOTIFICATION_READ", resource_id=own.pk).exists()


@pytest.mark.django_db
def test_unconfigured_machine_auth_fails_closed_and_human_jwt_is_not_machine_auth(user):
    _, pair = make_client_with_token(user)
    client = APIClient()
    response = client.post(
        "/api/v1/ai/detection-events/",
        {"service_ref": "AI_SERVICE"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {pair['access']}",
    )

    assert response.status_code == 503
    assert response.json()["code"] == "machine_authentication_unavailable"
    assert DetectionEvent.objects.count() == 0


@pytest.mark.django_db
def test_candidate_assignment_api_and_reads_are_reviewer_scoped(user, police_organization):
    assigner = get_user_model().objects.create_user(
        "candidate-admin@example.test", "local-test-password"
    )
    assigner.groups.add(Group.objects.get(name="ADMIN"))
    add_membership(assigner, police_organization)
    add_membership(user, police_organization)
    candidate = AccidentCandidate.objects.create(police_organization=police_organization)
    command_id = str(uuid4())
    admin_client, _ = make_client_with_token(assigner)

    response = admin_client.post(
        f"/api/v1/candidates/{candidate.pk}/assignment/",
        {"reviewer_id": str(user.pk), "command_id": command_id},
        format="json",
    )
    replay = admin_client.post(
        f"/api/v1/candidates/{candidate.pk}/assignment/",
        {"reviewer_id": str(user.pk), "command_id": command_id},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["data"]["candidate_id"] == str(candidate.pk)
    assert response.json()["data"]["reviewer_id"] == str(user.pk)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert (
        AuditEvent.objects.filter(
            action="CANDIDATE_REVIEWER_ASSIGNED", resource_id=candidate.pk
        ).count()
        == 1
    )

    reviewer_client, _ = make_client_with_token(user)
    listed = reviewer_client.get("/api/v1/candidates/")
    detail = reviewer_client.get(f"/api/v1/candidates/{candidate.pk}/")
    assert listed.status_code == detail.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["results"][0]["id"] == str(candidate.pk)
    assert detail.json()["id"] == str(candidate.pk)

    other_member = get_user_model().objects.create_user(
        "unassigned-police@example.test", "local-test-password"
    )
    add_membership(other_member, police_organization)
    other_client, _ = make_client_with_token(other_member)
    assert other_client.get("/api/v1/candidates/").json()["count"] == 0
    assert other_client.get(f"/api/v1/candidates/{candidate.pk}/").status_code == 404

    # ADMIN scope grants assignment authority, not access to every candidate.
    assert admin_client.get("/api/v1/candidates/").json()["count"] == 0

    reviewer_membership = OrganizationMembership.objects.get(
        user=user, organization=police_organization
    )
    reviewer_membership.status = MembershipStatus.SUSPENDED
    reviewer_membership.save(update_fields=["status", "updated_at"])
    assert reviewer_client.get("/api/v1/candidates/").json()["count"] == 0
    assert reviewer_client.get(f"/api/v1/candidates/{candidate.pk}/").status_code == 404


@pytest.mark.django_db
def test_candidate_assignment_api_rejects_non_admin_even_with_police_membership(
    user, police_organization
):
    add_membership(user, police_organization)
    reviewer = get_user_model().objects.create_user(
        "reviewer-target@example.test", "local-test-password"
    )
    add_membership(reviewer, police_organization)
    candidate = AccidentCandidate.objects.create(police_organization=police_organization)
    client, _ = make_client_with_token(user)

    response = client.post(
        f"/api/v1/candidates/{candidate.pk}/assignment/",
        {"reviewer_id": str(reviewer.pk), "command_id": str(uuid4())},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "authorization_denied"
    assert not CandidateReviewerAssignment.objects.filter(candidate=candidate).exists()
    assert AuditEvent.objects.filter(
        action="DOMAIN_ACTION_DENIED", resource_id=candidate.pk
    ).exists()


@pytest.mark.django_db
def test_test_machine_authenticator_is_explicit_and_never_proves_identity_from_body(
    user, video_source
):
    video_source.authorization_status = VideoSourceAuthorizationStatus.AUTHORIZED
    video_source.authorized_by_user = user
    video_source.authorized_at = timezone.now()
    video_source.authorization_reference = "test-approved-source"
    video_source.save(
        update_fields=[
            "authorization_status",
            "authorized_by_user",
            "authorized_at",
            "authorization_reference",
            "updated_at",
        ]
    )
    path = "api.v1.authentication.TestMachineCredentialAuthenticator"
    body = {
        "video_source_id": str(video_source.pk),
        "external_event_id": "api-machine-event",
        "model_name": "test-detector",
        "model_version": "1.0.0",
        "detected_at": timezone.now().isoformat(),
        "processing_outcome": "OBSERVATION",
        "service_ref": "CALLER_CONTROLLED_VALUE",
        "police_organization_id": str(uuid4()),
    }
    client = APIClient()
    machine_token = f"test-{uuid4().hex}"
    with override_settings(
        AI_SERVICE_AUTHENTICATOR=path,
        AI_TEST_MACHINE_TOKEN=machine_token,
    ):
        invalid = client.post(
            "/api/v1/ai/detection-events/",
            body,
            format="json",
            HTTP_AUTHORIZATION="Machine invalid-test-credential",
        )
        assert invalid.status_code == 401, invalid.content
        assert invalid.json()["code"] == "authentication_failed"
        assert not DetectionEvent.objects.filter(external_event_id="api-machine-event").exists()

        accepted = client.post(
            "/api/v1/ai/detection-events/",
            body,
            format="json",
            HTTP_AUTHORIZATION=f"Machine {machine_token}",
        )
    assert accepted.status_code == 201, accepted.content
    payload = accepted.json()
    assert set(payload) == {"id", "received_at"}
    assert "service_ref" not in payload

    event = DetectionEvent.objects.get(external_event_id="api-machine-event")

    assert event.service_principal_ref == "AI_SERVICE"

    with override_settings(
        AI_SERVICE_AUTHENTICATOR=path,
        AI_TEST_MACHINE_TOKEN=machine_token,
        TESTING=False,
    ):
        disabled = APIClient().post(
            "/api/v1/ai/detection-events/",
            body,
            format="json",
            HTTP_AUTHORIZATION=f"Machine {machine_token}",
        )
    assert disabled.status_code == 503
    assert disabled.json()["code"] == "machine_authentication_unavailable"


@pytest.mark.django_db
def test_unapproved_authority_endpoints_fail_closed_without_resource_disclosure(
    user, candidate, police_organization
):
    candidate.police_organization = police_organization
    candidate.save(update_fields=["police_organization", "updated_at"])
    other_police_organization = Organization.objects.create(
        code="other-police",
        display_name="Other Police",
        organization_kind="POLICE",
    )
    add_membership(user, other_police_organization)
    client, _ = make_client_with_token(user)
    existing = client.get(f"/api/v1/candidates/{candidate.pk}/")
    missing = client.get(f"/api/v1/candidates/{uuid4()}/")
    resolve = client.post(f"/api/v1/incidents/{uuid4()}/resolve/", {}, format="json")
    evidence = client.get(f"/api/v1/evidence/{uuid4()}/")
    location = client.get(f"/api/v1/incidents/{uuid4()}/locations/")
    cancel = client.post(f"/api/v1/assignments/{uuid4()}/cancel/", {}, format="json")

    assert existing.status_code == missing.status_code == 404
    assert existing.json()["code"] == missing.json()["code"] == "not_found"
    assert (
        resolve.status_code
        == evidence.status_code
        == location.status_code
        == cancel.status_code
        == 503
    )


@pytest.mark.django_db
def test_filter_allowlists_pagination_bounds_and_request_id_validation(user, incident):
    client, _ = make_client_with_token(user)
    invalid_filter = client.get("/api/v1/incidents/?status=ARBITRARY")
    assert invalid_filter.status_code == 400

    Notification.objects.bulk_create(
        [
            Notification(
                recipient_user=user,
                incident=incident,
                status=NotificationStatus.CREATED,
                safe_message_code=f"BATCH_{index}",
            )
            for index in range(105)
        ]
    )
    listing = client.get("/api/v1/notifications/?limit=500", HTTP_X_REQUEST_ID="not-a-uuid")
    assert listing.status_code == 200
    assert len(listing.json()["results"]) == 100
    assert listing.json()["next"] is not None
    assert listing["X-Request-ID"] != "not-a-uuid"

    valid_id = str(uuid4())
    correlated = client.get("/api/v1/notifications/?limit=1", HTTP_X_REQUEST_ID=valid_id)
    assert correlated["X-Request-ID"] == valid_id


@pytest.mark.django_db
def test_login_throttle_returns_standard_429_envelope(user):
    client = APIClient()
    responses = [
        client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": "wrong-password"},
            format="json",
        )
        for _ in range(6)
    ]

    assert [response.status_code for response in responses[:5]] == [401] * 5
    assert responses[5].status_code == 429
    assert responses[5].json()["code"] == "rate_limited"


@pytest.mark.django_db
@pytest.mark.parametrize("invocation", ("first", "second"))
def test_login_throttle_budget_is_isolated_between_api_test_invocations(user, invocation):
    client = APIClient()
    for attempt in range(4):
        response = client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": f"wrong-password-{attempt}"},
            format="json",
        )
        assert response.status_code == 401, f"{invocation} attempt {attempt}: {response.content}"

    valid = client.post(
        "/api/v1/auth/token/",
        {"email": user.email, "password": "local-test-password"},
        format="json",
    )
    assert valid.status_code == 200, f"{invocation}: {valid.content}"


@pytest.mark.django_db
def test_request_body_limit_returns_safe_413_error():
    client = APIClient()
    body = b'{"email":"large@example.test","password":"' + b"x" * 1_100_000 + b'"}'
    response = client.generic("POST", "/api/v1/auth/token/", body, content_type="application/json")

    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"
