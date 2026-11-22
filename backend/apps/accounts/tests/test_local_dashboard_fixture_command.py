import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import override_settings
from django.utils import timezone

from apps.accounts.management.commands.setup_local_dashboard_test_data import (
    EMAIL_VARIABLES,
    FIXTURE_ORGANIZATION_CODES,
    FIXTURE_ORGANIZATION_NAMES,
    FIXTURE_SOURCE_CODE,
    MANAGED_GROUP,
    Command,
)
from apps.audit.models import AuditEvent
from apps.detection.models import DetectionEvent
from apps.incidents.models import AccidentCandidate, AccidentIncident, CandidateReview
from apps.organizations.models import MembershipStatus, Organization, OrganizationMembership
from apps.responses.models import AssignmentStatus, ResponseAssignment
from apps.sources.models import VideoSource, VideoSourceAuthorizationStatus, VideoSourceType

User = get_user_model()
FIXTURE_PASSWORD = "Local-Fixture-Test-Password-2026!"
FIXTURE_EMAILS = {
    "generic": "dashboard.auth@resqvision.test",
    "admin": "dashboard.admin@resqvision.test",
    "police": "dashboard.police@resqvision.test",
    "hospital": "dashboard.hospital@resqvision.test",
}


def _configure_fixture_environment(monkeypatch):
    monkeypatch.setenv("RESQVISION_LOCAL_TEST_DATA_OPT_IN", "1")
    for key, (email_variable, password_variable, _) in EMAIL_VARIABLES.items():
        monkeypatch.setenv(email_variable, FIXTURE_EMAILS[key])
        monkeypatch.setenv(password_variable, FIXTURE_PASSWORD)


def _create_role_groups():
    return {
        name: Group.objects.get_or_create(name=name)[0] for name in ("ADMIN", "POLICE", "HOSPITAL")
    }


def _create_managed_users(*, role_groups, emails=FIXTURE_EMAILS):
    managed_group = Group.objects.create(name=MANAGED_GROUP)
    users = {}
    for key, (_, _, role) in EMAIL_VARIABLES.items():
        user = User.objects.create_user(email=emails[key], password=FIXTURE_PASSWORD)
        user.groups.add(managed_group)
        if role:
            user.groups.add(role_groups[role])
        users[key] = user
    return users


def _create_fixture_organizations(codes=FIXTURE_ORGANIZATION_CODES):
    return {
        kind: Organization.objects.create(
            code=codes[kind],
            display_name=FIXTURE_ORGANIZATION_NAMES[kind],
            organization_kind=kind,
        )
        for kind in ("POLICE", "HOSPITAL", "SOURCE_OWNER")
    }


def _create_expected_memberships(users, role_groups, organizations):
    OrganizationMembership.objects.create(
        user=users["police"],
        organization=organizations["POLICE"],
        role_group=role_groups["POLICE"],
        status=MembershipStatus.ACTIVE,
    )
    OrganizationMembership.objects.create(
        user=users["hospital"],
        organization=organizations["HOSPITAL"],
        role_group=role_groups["HOSPITAL"],
        status=MembershipStatus.ACTIVE,
    )
    OrganizationMembership.objects.create(
        user=users["admin"],
        organization=organizations["POLICE"],
        role_group=role_groups["POLICE"],
        status=MembershipStatus.SUSPENDED,
    )


def _run_fixture_command(monkeypatch):
    monkeypatch.setattr(Command, "_require_local_database", lambda self: None)
    call_command("setup_local_dashboard_test_data", verbosity=0)


@pytest.mark.django_db
def test_local_fixture_command_requires_explicit_opt_in_without_writes(monkeypatch):
    monkeypatch.delenv("RESQVISION_LOCAL_TEST_DATA_OPT_IN", raising=False)
    with override_settings(DEBUG=True):
        users_before = User.objects.count()
        with pytest.raises(CommandError, match="opt in to local fixture creation"):
            call_command("setup_local_dashboard_test_data", verbosity=0)
        assert User.objects.count() == users_before


@pytest.mark.django_db
def test_local_fixture_command_refuses_debug_false_without_writes(monkeypatch):
    monkeypatch.setenv("RESQVISION_LOCAL_TEST_DATA_OPT_IN", "1")
    users_before = User.objects.count()
    with override_settings(DEBUG=False):
        with pytest.raises(CommandError, match="unless DEBUG=True"):
            call_command("setup_local_dashboard_test_data", verbosity=0)
    assert User.objects.count() == users_before


@pytest.mark.django_db
def test_fixture_command_refuses_changed_managed_emails_before_creating_accounts(monkeypatch):
    _configure_fixture_environment(monkeypatch)
    _create_role_groups()
    managed_group = Group.objects.create(name=MANAGED_GROUP)
    existing_user = User.objects.create_user(
        email="existing.generic@resqvision.test",
        password=FIXTURE_PASSWORD,
    )
    existing_user.groups.add(managed_group)
    users_before = User.objects.count()
    organizations_before = Organization.objects.count()

    with (
        override_settings(DEBUG=True, AUTH_PASSWORD_VALIDATORS=[]),
        pytest.raises(CommandError, match="Refusing to create replacement accounts"),
    ):
        _run_fixture_command(monkeypatch)

    assert User.objects.count() == users_before
    assert Organization.objects.count() == organizations_before


@pytest.mark.django_db
def test_fixture_command_refuses_changed_organization_codes_before_creating_replacements(
    monkeypatch,
):
    _configure_fixture_environment(monkeypatch)
    role_groups = _create_role_groups()
    users = _create_managed_users(role_groups=role_groups)
    previous_codes = {
        "POLICE": "prior-local-police",
        "HOSPITAL": "prior-local-hospital",
        "SOURCE_OWNER": "prior-local-source-owner",
    }
    organizations = _create_fixture_organizations(previous_codes)
    _create_expected_memberships(users, role_groups, organizations)
    organizations_before = Organization.objects.count()

    with (
        override_settings(DEBUG=True, AUTH_PASSWORD_VALIDATORS=[]),
        pytest.raises(CommandError, match="Refusing to create replacement organizations"),
    ):
        _run_fixture_command(monkeypatch)

    assert User.objects.count() == 4
    assert Organization.objects.count() == organizations_before
    assert VideoSource.objects.count() == 0


@pytest.mark.django_db
def test_fixture_command_refuses_orphaned_local_organization_before_creating_accounts(
    monkeypatch,
):
    _configure_fixture_environment(monkeypatch)
    _create_role_groups()
    Organization.objects.create(
        code="resqvision-local-prior-police",
        display_name="Existing Local Police Organization",
        organization_kind="POLICE",
    )

    with (
        override_settings(DEBUG=True, AUTH_PASSWORD_VALIDATORS=[]),
        pytest.raises(CommandError, match="Refusing to create a replacement organization"),
    ):
        _run_fixture_command(monkeypatch)

    assert User.objects.count() == 0
    assert Organization.objects.count() == 1


@pytest.mark.django_db
def test_fixture_command_refuses_changed_source_code_before_registering_replacement(
    monkeypatch,
):
    _configure_fixture_environment(monkeypatch)
    role_groups = _create_role_groups()
    users = _create_managed_users(role_groups=role_groups)
    organizations = _create_fixture_organizations()
    _create_expected_memberships(users, role_groups, organizations)
    VideoSource.objects.create(
        source_code="prior-local-source",
        name="Existing local controlled source",
        source_type=VideoSourceType.CONTROLLED_FILE,
        owner_organization=organizations["SOURCE_OWNER"],
        authorization_status=VideoSourceAuthorizationStatus.AUTHORIZED,
        authorized_by_user=users["admin"],
        authorized_at=timezone.now(),
        authorization_reference="Existing local authorization record",
        processing_policy_ref="local-test-only-processing-v1",
        retention_policy_ref="local-test-only-retention-v1",
    )

    with (
        override_settings(DEBUG=True, AUTH_PASSWORD_VALIDATORS=[]),
        pytest.raises(CommandError, match="Refusing to register a replacement"),
    ):
        _run_fixture_command(monkeypatch)

    assert User.objects.count() == 4
    assert Organization.objects.count() == 3
    assert VideoSource.objects.count() == 1
    assert DetectionEvent.objects.count() == 0


@pytest.mark.django_db
def test_fixture_command_rerun_reuses_records_with_same_identifiers_and_credentials(monkeypatch):
    _configure_fixture_environment(monkeypatch)
    _create_role_groups()
    with override_settings(DEBUG=True, AUTH_PASSWORD_VALIDATORS=[]):
        _run_fixture_command(monkeypatch)
        organization = Organization.objects.get(code=FIXTURE_ORGANIZATION_CODES["POLICE"])
        organization.display_name = "Locally Renamed Police Display"
        organization.save(update_fields=["display_name"])
        source = VideoSource.objects.get(source_code=FIXTURE_SOURCE_CODE)
        source.name = "Locally Renamed Source Display"
        source.authorization_reference = "Existing local authorization record"
        source.save(update_fields=["name", "authorization_reference"])
        event = DetectionEvent.objects.order_by("detected_at").first()
        event.external_event_id = "legacy-dashboard-event-001"
        event.auxiliary_metadata = {"fixture": "legacy_dashboard", "retained": True}
        event.save(update_fields=["external_event_id", "auxiliary_metadata"])
        review = CandidateReview.objects.order_by("reviewed_at").first()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE incidents_candidate_review SET rationale = %s WHERE id = %s",
                ["Historical rationale retained.", review.pk],
            )
        audit_count = AuditEvent.objects.count()
        original_ids = {
            "users": set(User.objects.values_list("pk", flat=True)),
            "organizations": set(Organization.objects.values_list("pk", flat=True)),
            "sources": set(VideoSource.objects.values_list("pk", flat=True)),
            "events": set(DetectionEvent.objects.values_list("pk", flat=True)),
            "candidates": set(AccidentCandidate.objects.values_list("pk", flat=True)),
            "incidents": set(AccidentIncident.objects.values_list("pk", flat=True)),
            "assignments": set(ResponseAssignment.objects.values_list("pk", flat=True)),
        }
        _run_fixture_command(monkeypatch)

    assert User.objects.count() == 4
    assert Organization.objects.count() == 3
    organization.refresh_from_db()
    assert organization.display_name == "Locally Renamed Police Display"
    assert VideoSource.objects.count() == 1
    source.refresh_from_db()
    assert source.name == "Locally Renamed Source Display"
    assert source.authorization_reference == "Existing local authorization record"
    assert DetectionEvent.objects.count() == 6
    assert AccidentCandidate.objects.count() == 6
    assert AccidentIncident.objects.count() == 6
    assert ResponseAssignment.objects.count() == 12
    assert AuditEvent.objects.count() == audit_count
    assert set(User.objects.values_list("pk", flat=True)) == original_ids["users"]
    assert set(Organization.objects.values_list("pk", flat=True)) == original_ids["organizations"]
    assert set(VideoSource.objects.values_list("pk", flat=True)) == original_ids["sources"]
    assert set(DetectionEvent.objects.values_list("pk", flat=True)) == original_ids["events"]
    assert set(AccidentCandidate.objects.values_list("pk", flat=True)) == original_ids["candidates"]
    assert set(AccidentIncident.objects.values_list("pk", flat=True)) == original_ids["incidents"]
    assert (
        set(ResponseAssignment.objects.values_list("pk", flat=True)) == original_ids["assignments"]
    )
    event.refresh_from_db()
    assert event.external_event_id == "legacy-dashboard-event-001"
    assert event.auxiliary_metadata == {"fixture": "legacy_dashboard", "retained": True}
    review.refresh_from_db()
    assert review.rationale == "Historical rationale retained."
    assert all(user.check_password(FIXTURE_PASSWORD) for user in User.objects.all())


@pytest.mark.django_db
def test_fixture_command_reuses_legacy_event_identity_without_ingesting_replacement(
    monkeypatch,
):
    _configure_fixture_environment(monkeypatch)
    _create_role_groups()
    with override_settings(DEBUG=True, AUTH_PASSWORD_VALIDATORS=[]):
        _run_fixture_command(monkeypatch)
        event = DetectionEvent.objects.order_by("detected_at").first()
        event.external_event_id = "prior-local-event-001"
        event.save(update_fields=["external_event_id"])
        audit_count = AuditEvent.objects.count()
        _run_fixture_command(monkeypatch)

    assert DetectionEvent.objects.count() == 6
    assert AccidentCandidate.objects.count() == 6
    assert AccidentIncident.objects.count() == 6
    assert ResponseAssignment.objects.count() == 12
    assert AuditEvent.objects.count() == audit_count
    event.refresh_from_db()
    assert event.external_event_id == "prior-local-event-001"


@pytest.mark.django_db
def test_fixture_command_rejects_incomplete_existing_graph_without_writes(monkeypatch):
    _configure_fixture_environment(monkeypatch)
    _create_role_groups()
    with override_settings(DEBUG=True, AUTH_PASSWORD_VALIDATORS=[]):
        _run_fixture_command(monkeypatch)
        assignment = ResponseAssignment.objects.first()
        ResponseAssignment.objects.filter(pk=assignment.pk).update(
            status=AssignmentStatus.CANCELLED
        )
        before = (
            User.objects.count(),
            Organization.objects.count(),
            VideoSource.objects.count(),
            DetectionEvent.objects.count(),
            AccidentCandidate.objects.count(),
            AccidentIncident.objects.count(),
            ResponseAssignment.objects.count(),
            AuditEvent.objects.count(),
        )

        with pytest.raises(CommandError, match="existing fixture assignment is incomplete"):
            _run_fixture_command(monkeypatch)

    assert before == (
        User.objects.count(),
        Organization.objects.count(),
        VideoSource.objects.count(),
        DetectionEvent.objects.count(),
        AccidentCandidate.objects.count(),
        AccidentIncident.objects.count(),
        ResponseAssignment.objects.count(),
        AuditEvent.objects.count(),
    )


@pytest.mark.django_db
def test_fixture_command_does_not_rotate_credentials_during_reuse(monkeypatch):
    _configure_fixture_environment(monkeypatch)
    _create_role_groups()
    with override_settings(DEBUG=True, AUTH_PASSWORD_VALIDATORS=[]):
        _run_fixture_command(monkeypatch)
        before_hashes = dict(User.objects.values_list("email", "password"))
        with pytest.raises(CommandError, match="Credential rotation is unavailable"):
            call_command(
                "setup_local_dashboard_test_data",
                rotate_managed_test_passwords=True,
                verbosity=0,
            )
    assert dict(User.objects.values_list("email", "password")) == before_hashes
