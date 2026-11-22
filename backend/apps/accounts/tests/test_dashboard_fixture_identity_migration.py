from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from uuid import UUID, uuid5

import pytest
from django.contrib.auth.models import Group
from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone

from apps.accounts.management.commands.setup_local_dashboard_test_data import (
    FIXTURE_NAMESPACE,
    _LocalFixturePolicy,
)
from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services.events import record_successful_action
from apps.detection.models import DetectionEvent
from apps.incidents.models import (
    AccidentIncident,
    CandidateDetectionEvent,
    CandidateReview,
    IncidentStatusHistory,
)
from apps.incidents.services import begin_candidate_review, create_candidate, verify_candidate
from apps.organizations.models import Organization, OrganizationMembership
from apps.responses.models import AssignmentStatusHistory, ResponseAssignment
from apps.responses.services import create_assignment
from apps.sources.models import VideoSource, VideoSourceAvailabilityStatus
from common.domain.actors import HumanActor, MachineActor
from common.domain.authorization import AI_SERVICE_REF

migration = import_module("apps.accounts.migrations.0003_reconcile_dashboard_fixture_identity")
USER_IDS = {
    "generic": UUID("4e90729d-16f0-406e-a9c9-d59650eb4bf7"),
    "admin": UUID("58343c9f-9e45-4449-950c-0ea56e3913c4"),
    "police": UUID("70c2514e-ca60-4c28-baa3-b6a0063b0e23"),
    "hospital": UUID("e590263d-03cf-4df7-b1e8-6c2ef7d84ccc"),
}
ORGANIZATION_IDS = {
    "POLICE": UUID("1b228cb9-becf-4405-9926-437ccb66012e"),
    "HOSPITAL": UUID("637b2520-6b3d-4498-853f-34e38c33e8e9"),
    "SOURCE_OWNER": UUID("4bbde553-ddcd-470a-812e-8105b01b47fa"),
}
SOURCE_ID = UUID("b745b497-19f7-4171-bdeb-c8101a2be8d2")
EVENT_IDS = migration.EVENT_IDS
LEGACY_EMAILS = {
    "generic": "old.auth@resqvision.test",
    "admin": "old.admin@resqvision.test",
    "police": "old.police@resqvision.test",
    "hospital": "old.hospital@resqvision.test",
}
LEGACY_ORGANIZATION_CODES = {
    "POLICE": "resqvision-local-old-police",
    "HOSPITAL": "resqvision-local-old-hospital",
    "SOURCE_OWNER": "resqvision-local-old-source-owner",
}
LEGACY_SOURCE_CODE = "resqvision-local-old-source"
FIXTURE_PASSWORD = "Migration-Fixture-Password-2026!"


def _migration_apps():
    loader = MigrationLoader(connection)
    return loader.project_state([("accounts", "0003_reconcile_dashboard_fixture_identity")]).apps


def _schema_editor_stub():
    def execute(sql, params=None):
        with connection.cursor() as cursor:
            cursor.execute(sql, params)

    return SimpleNamespace(connection=connection, execute=execute)


def _create_fixture_graph():
    role_groups = {
        name: Group.objects.get_or_create(name=name)[0]
        for name in ("ADMIN", "POLICE", "HOSPITAL", "RESQVISION_LOCAL_INTEGRATION_TEST")
    }
    users = {}
    roles = {
        "generic": None,
        "admin": "ADMIN",
        "police": "POLICE",
        "hospital": "HOSPITAL",
    }
    for key, user_id in USER_IDS.items():
        user = User.objects.create_user(
            email=LEGACY_EMAILS[key],
            password=FIXTURE_PASSWORD,
            id=user_id,
        )
        user.groups.add(role_groups["RESQVISION_LOCAL_INTEGRATION_TEST"])
        if roles[key]:
            user.groups.add(role_groups[roles[key]])
        users[key] = user

    organizations = {}
    for kind, organization_id in ORGANIZATION_IDS.items():
        organizations[kind] = Organization.objects.create(
            id=organization_id,
            code=LEGACY_ORGANIZATION_CODES[kind],
            display_name=f"Preserved {kind.title()} Display",
            organization_kind=kind,
        )
    OrganizationMembership.objects.create(
        user=users["admin"],
        organization=organizations["POLICE"],
        role_group=role_groups["POLICE"],
        status="SUSPENDED",
    )
    OrganizationMembership.objects.create(
        user=users["police"],
        organization=organizations["POLICE"],
        role_group=role_groups["POLICE"],
        status="ACTIVE",
    )
    OrganizationMembership.objects.create(
        user=users["hospital"],
        organization=organizations["HOSPITAL"],
        role_group=role_groups["HOSPITAL"],
        status="ACTIVE",
    )

    source = VideoSource.objects.create(
        id=SOURCE_ID,
        source_code=LEGACY_SOURCE_CODE,
        name="Display name to preserve",
        source_type="CONTROLLED_FILE",
        availability_status=VideoSourceAvailabilityStatus.AVAILABLE,
        owner_organization=organizations["SOURCE_OWNER"],
        designated_police_organization=organizations["POLICE"],
        authorization_status="AUTHORIZED",
        authorized_by_user=users["admin"],
        authorized_at=timezone.now(),
        authorization_reference="Historical approval reference",
        processing_policy_ref="local-test-only-processing-v1",
        retention_policy_ref="local-test-only-retention-v1",
    )
    human = HumanActor(users["admin"])
    record_successful_action(
        actor=human,
        action="VIDEO_SOURCE_REGISTERED",
        resource_type="VIDEO_SOURCE",
        resource_id=source.pk,
    )
    record_successful_action(
        actor=human,
        action="VIDEO_SOURCE_AUTHORIZED",
        resource_type="VIDEO_SOURCE",
        resource_id=source.pk,
    )

    policy = _LocalFixturePolicy(users["admin"].pk)
    machine = MachineActor(AI_SERVICE_REF)
    for number, event_id in enumerate(EVENT_IDS, start=1):
        event = DetectionEvent.objects.create(
            id=event_id,
            video_source=source,
            external_event_id=f"legacy-event-{number:03d}",
            service_principal_ref=AI_SERVICE_REF,
            model_name=migration.MODEL_NAME,
            model_version=migration.MODEL_VERSION,
            detected_at=migration.FIRST_EVENT_AT + timedelta(minutes=number - 1),
            processing_outcome="OBSERVATION",
            auxiliary_metadata={"fixture": "legacy_payload"},
        )
        record_successful_action(
            actor=machine,
            action="DETECTION_EVENT_ACCEPTED",
            resource_type="DETECTION_EVENT",
            resource_id=event.pk,
        )
        candidate = create_candidate(detection_event_id=event.pk, actor=machine, policy=policy)
        suffix = "" if number == 1 else f"-{number:03d}"
        begin_candidate_review(
            candidate_id=candidate.pk,
            actor=human,
            command_id=uuid5(FIXTURE_NAMESPACE, f"candidate-review{suffix}"),
            policy=policy,
        )
        incident = verify_candidate(
            candidate_id=candidate.pk,
            actor=human,
            command_id=uuid5(FIXTURE_NAMESPACE, f"candidate-verify{suffix}"),
            rationale="Historical review decision.",
            policy=policy,
        ).value
        for kind in ("POLICE", "HOSPITAL"):
            create_assignment(
                incident_id=incident.pk,
                target_organization_id=organizations[kind].pk,
                actor=human,
                command_id=uuid5(
                    FIXTURE_NAMESPACE,
                    f"assignment-{kind.lower()}{suffix}",
                ),
                policy=policy,
            )
    return users, organizations, source


def _relationship_snapshot():
    return {
        "users": set(User.objects.values_list("pk", flat=True)),
        "groups": set(
            User.objects.values_list("pk", "groups__name").order_by("pk", "groups__name")
        ),
        "memberships": set(
            OrganizationMembership.objects.values_list(
                "pk", "user_id", "organization_id", "role_group_id", "status"
            )
        ),
        "organizations": set(Organization.objects.values_list("pk", "organization_kind")),
        "source": set(
            VideoSource.objects.values_list(
                "pk",
                "owner_organization_id",
                "designated_police_organization_id",
                "authorized_by_user_id",
                "authorization_reference",
                "name",
            )
        ),
        "events": set(DetectionEvent.objects.values_list("pk", "video_source_id")),
        "links": set(
            CandidateDetectionEvent.objects.values_list("pk", "candidate_id", "detection_event_id")
        ),
        "reviews": set(
            CandidateReview.objects.values_list("pk", "candidate_id", "reviewer_id", "command_id")
        ),
        "incidents": set(AccidentIncident.objects.values_list("pk", "candidate_id", "status")),
        "incident_history": set(
            IncidentStatusHistory.objects.values_list("pk", "incident_id", "command_id")
        ),
        "assignments": set(
            ResponseAssignment.objects.values_list(
                "pk", "incident_id", "target_organization_id", "creation_command_id"
            )
        ),
        "assignment_history": set(
            AssignmentStatusHistory.objects.values_list(
                "pk", "response_assignment_id", "command_id"
            )
        ),
        "audit": set(
            AuditEvent.objects.values_list("pk", "action", "resource_type", "resource_id")
        ),
    }


@pytest.mark.django_db
def test_identity_migration_preserves_ids_relationships_credentials_and_rolls_back():
    users, organizations, source = _create_fixture_graph()
    before = _relationship_snapshot()
    password_hashes = {key: user.password for key, user in users.items()}
    display_names = {key: organization.display_name for key, organization in organizations.items()}
    source_display = (source.name, source.authorization_reference)
    apps = _migration_apps()
    editor = _schema_editor_stub()

    with transaction.atomic():
        migration.reconcile_identity_values(apps, editor)

    for user_id, target in migration.USER_IDENTITIES.items():
        assert User.objects.get(pk=user_id).email == target
    for organization_id, (target, _) in migration.ORGANIZATION_IDENTITIES.items():
        assert Organization.objects.get(pk=organization_id).code == target
    assert VideoSource.objects.get(pk=SOURCE_ID).source_code == migration.SOURCE_CODE
    assert _relationship_snapshot() == before
    assert {
        key: User.objects.get(pk=user.pk).password for key, user in users.items()
    } == password_hashes
    assert {
        key: Organization.objects.get(pk=value.pk).display_name
        for key, value in organizations.items()
    } == display_names
    source.refresh_from_db()
    assert (source.name, source.authorization_reference) == source_display
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM accounts_dashboard_fixture_identity_rollback")
        assert cursor.fetchone()[0] == 8

    with transaction.atomic():
        migration.restore_identity_values(apps, editor)

    for key, user in users.items():
        assert User.objects.get(pk=user.pk).email == LEGACY_EMAILS[key]
    for key, organization in organizations.items():
        assert Organization.objects.get(pk=organization.pk).code == LEGACY_ORGANIZATION_CODES[key]
    assert VideoSource.objects.get(pk=SOURCE_ID).source_code == LEGACY_SOURCE_CODE
    assert _relationship_snapshot() == before
    assert {
        key: User.objects.get(pk=user.pk).password for key, user in users.items()
    } == password_hashes
    assert (
        "accounts_dashboard_fixture_identity_rollback" not in connection.introspection.table_names()
    )


@pytest.mark.django_db
def test_identity_migration_rejects_partial_fixture_before_writing():
    managed_group = Group.objects.create(name="RESQVISION_LOCAL_INTEGRATION_TEST")
    user = User.objects.create_user(
        email="partial.auth@resqvision.test",
        password=FIXTURE_PASSWORD,
        id=USER_IDS["generic"],
    )
    user.groups.add(managed_group)
    apps = _migration_apps()
    editor = _schema_editor_stub()

    with pytest.raises(RuntimeError, match="identity records are incomplete"):
        migration.reconcile_identity_values(apps, editor)

    user.refresh_from_db()
    assert user.email == "partial.auth@resqvision.test"
    assert (
        "accounts_dashboard_fixture_identity_rollback" not in connection.introspection.table_names()
    )
    assert Organization.objects.count() == 0
    assert VideoSource.objects.count() == 0
    assert DetectionEvent.objects.count() == 0
