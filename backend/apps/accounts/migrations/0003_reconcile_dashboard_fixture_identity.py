"""Reconcile audited local dashboard identities without replacing fixture rows."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

from django.conf import settings
from django.db import migrations

NAMESPACE = UUID("879c61e8-97e7-4f2f-9d92-a55009dd835d")
USER_IDENTITIES = {
    UUID("4e90729d-16f0-406e-a9c9-d59650eb4bf7"): "dashboard.auth@resqvision.test",
    UUID("58343c9f-9e45-4449-950c-0ea56e3913c4"): "dashboard.admin@resqvision.test",
    UUID("70c2514e-ca60-4c28-baa3-b6a0063b0e23"): "dashboard.police@resqvision.test",
    UUID("e590263d-03cf-4df7-b1e8-6c2ef7d84ccc"): "dashboard.hospital@resqvision.test",
}
ORGANIZATION_IDENTITIES = {
    UUID("1b228cb9-becf-4405-9926-437ccb66012e"): (
        "resqvision-local-dashboard-police",
        "POLICE",
    ),
    UUID("637b2520-6b3d-4498-853f-34e38c33e8e9"): (
        "resqvision-local-dashboard-hospital",
        "HOSPITAL",
    ),
    UUID("4bbde553-ddcd-470a-812e-8105b01b47fa"): (
        "resqvision-local-dashboard-source-owner",
        "SOURCE_OWNER",
    ),
}
SOURCE_ID = UUID("b745b497-19f7-4171-bdeb-c8101a2be8d2")
SOURCE_CODE = "resqvision-local-dashboard-source"
ROLLBACK_TABLE = "accounts_dashboard_fixture_identity_rollback"
MANAGED_GROUP = "RESQVISION_LOCAL_INTEGRATION_TEST"
FIRST_EVENT_AT = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
EVENT_COUNT = 6
MODEL_NAME = "resqvision-local-test-model"
MODEL_VERSION = "1.0-test"
EVENT_IDS = tuple(
    UUID(value)
    for value in (
        "93e4f978-28fb-44c1-8e49-a2a34342da16",
        "d2b331aa-ebcb-435b-98b8-96b728b2952d",
        "c469d07e-067d-47cd-8558-376d085a704d",
        "dfc42a1d-27d8-4c3e-824f-1e6271787ee5",
        "b938f344-5ceb-4e55-b2c1-3078e1bbdc4f",
        "66ae1a97-2930-4375-970d-6ca1c9e0f53d",
    )
)


def _command_ids(kind):
    values = []
    for number in range(1, EVENT_COUNT + 1):
        suffix = "" if number == 1 else f"-{number:03d}"
        if kind == "verify":
            values.append(uuid5(NAMESPACE, f"candidate-verify{suffix}"))
        elif kind == "review":
            values.append(uuid5(NAMESPACE, f"candidate-review{suffix}"))
        else:
            values.extend(
                uuid5(NAMESPACE, f"assignment-{target}{suffix}")
                for target in ("police", "hospital")
            )
    return values


def _fixture_exists(apps, database):
    User = apps.get_model("accounts", "User")
    Organization = apps.get_model("organizations", "Organization")
    VideoSource = apps.get_model("sources", "VideoSource")
    DetectionEvent = apps.get_model("detection", "DetectionEvent")
    CandidateReview = apps.get_model("incidents", "CandidateReview")
    IncidentStatusHistory = apps.get_model("incidents", "IncidentStatusHistory")
    ResponseAssignment = apps.get_model("responses", "ResponseAssignment")
    AssignmentStatusHistory = apps.get_model("responses", "AssignmentStatusHistory")
    AuditEvent = apps.get_model("audit", "AuditEvent")
    Group = apps.get_model("auth", "Group")
    audit_resource_ids = (
        tuple(USER_IDENTITIES)
        + tuple(ORGANIZATION_IDENTITIES)
        + (
            SOURCE_ID,
            *EVENT_IDS,
        )
    )
    audit_command_ids = [
        str(value) for kind in ("review", "verify", "assignment") for value in _command_ids(kind)
    ]

    return any(
        (
            User.objects.using(database).filter(pk__in=USER_IDENTITIES).exists(),
            User.objects.using(database).filter(email__in=tuple(USER_IDENTITIES.values())).exists(),
            Organization.objects.using(database).filter(pk__in=ORGANIZATION_IDENTITIES).exists(),
            Organization.objects.using(database)
            .filter(code__in=[value[0] for value in ORGANIZATION_IDENTITIES.values()])
            .exists(),
            VideoSource.objects.using(database).filter(pk=SOURCE_ID).exists(),
            VideoSource.objects.using(database).filter(source_code=SOURCE_CODE).exists(),
            DetectionEvent.objects.using(database).filter(pk__in=EVENT_IDS).exists(),
            CandidateReview.objects.using(database)
            .filter(command_id__in=_command_ids("verify"))
            .exists(),
            IncidentStatusHistory.objects.using(database)
            .filter(command_id__in=_command_ids("verify"))
            .exists(),
            ResponseAssignment.objects.using(database)
            .filter(creation_command_id__in=_command_ids("assignment"))
            .exists(),
            AssignmentStatusHistory.objects.using(database)
            .filter(command_id__in=_command_ids("assignment"))
            .exists(),
            AuditEvent.objects.using(database).filter(resource_id__in=audit_resource_ids).exists(),
            AuditEvent.objects.using(database)
            .filter(safe_context__command_id__in=audit_command_ids)
            .exists(),
            Group.objects.using(database).filter(name=MANAGED_GROUP).exists(),
        )
    )


def _fail_if(condition, message):
    if condition:
        raise RuntimeError(message)


def _require_audit(AuditEvent, *, action, resource_type, resource_id, command_id=None):
    events = AuditEvent.objects.filter(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome="SUCCESS",
    )
    if command_id is not None:
        events = events.filter(safe_context__command_id=str(command_id))
    _fail_if(not events.exists(), f"Fixture audit history is incomplete for {action}.")


def reconcile_identity_values(apps, schema_editor):
    database = schema_editor.connection.alias
    User = apps.get_model("accounts", "User")
    Group = apps.get_model("auth", "Group")
    Organization = apps.get_model("organizations", "Organization")
    Membership = apps.get_model("organizations", "OrganizationMembership")
    VideoSource = apps.get_model("sources", "VideoSource")
    DetectionEvent = apps.get_model("detection", "DetectionEvent")
    Candidate = apps.get_model("incidents", "AccidentCandidate")
    CandidateLink = apps.get_model("incidents", "CandidateDetectionEvent")
    CandidateReview = apps.get_model("incidents", "CandidateReview")
    Incident = apps.get_model("incidents", "AccidentIncident")
    IncidentHistory = apps.get_model("incidents", "IncidentStatusHistory")
    Assignment = apps.get_model("responses", "ResponseAssignment")
    AssignmentHistory = apps.get_model("responses", "AssignmentStatusHistory")
    AuditEvent = apps.get_model("audit", "AuditEvent")

    if not _fixture_exists(apps, database):
        return

    users = {
        user_id: User.objects.using(database).filter(pk=user_id).first()
        for user_id in USER_IDENTITIES
    }
    organizations = {
        organization_id: Organization.objects.using(database).filter(pk=organization_id).first()
        for organization_id in ORGANIZATION_IDENTITIES
    }
    source = VideoSource.objects.using(database).filter(pk=SOURCE_ID).first()
    _fail_if(
        any(user is None for user in users.values())
        or any(organization is None for organization in organizations.values())
        or source is None,
        "Fixture identity records are incomplete; no values were changed.",
    )

    for user_id, user in users.items():
        _fail_if(
            not user.email.endswith(".test")
            or not user.is_active
            or user.is_staff
            or user.is_superuser
            or user.user_permissions.using(database).exists(),
            "A managed fixture account has unexpected state.",
        )
        _fail_if(
            User.objects.using(database)
            .filter(email=USER_IDENTITIES[user_id])
            .exclude(pk=user_id)
            .exists(),
            "A target account identity belongs to another user.",
        )

    role_groups = {
        name: Group.objects.using(database).filter(name=name).first()
        for name in ("ADMIN", "POLICE", "HOSPITAL", MANAGED_GROUP)
    }
    _fail_if(any(group is None for group in role_groups.values()), "Fixture groups are missing.")
    _fail_if(
        any(group.permissions.using(database).exists() for group in role_groups.values()),
        "A fixture group grants permissions.",
    )
    expected_groups = {
        UUID("4e90729d-16f0-406e-a9c9-d59650eb4bf7"): {MANAGED_GROUP},
        UUID("58343c9f-9e45-4449-950c-0ea56e3913c4"): {MANAGED_GROUP, "ADMIN"},
        UUID("70c2514e-ca60-4c28-baa3-b6a0063b0e23"): {MANAGED_GROUP, "POLICE"},
        UUID("e590263d-03cf-4df7-b1e8-6c2ef7d84ccc"): {MANAGED_GROUP, "HOSPITAL"},
    }
    group_ids = {name: group.pk for name, group in role_groups.items()}
    for user_id, names in expected_groups.items():
        actual = set(users[user_id].groups.using(database).values_list("name", flat=True))
        _fail_if(actual != names, "A managed fixture account has unexpected role groups.")

    for organization_id, (target_code, kind) in ORGANIZATION_IDENTITIES.items():
        organization = organizations[organization_id]
        _fail_if(
            organization.organization_kind != kind
            or not organization.is_active
            or not organization.code.startswith("resqvision-local-")
            or len(organization.code) > 80,
            "A managed fixture organization has unexpected identity or state.",
        )
        _fail_if(
            Organization.objects.using(database)
            .filter(code=target_code)
            .exclude(pk=organization_id)
            .exists(),
            "A target organization identity belongs to another row.",
        )
        _fail_if(
            Organization.objects.using(database)
            .filter(organization_kind=kind, code__startswith="resqvision-local-")
            .exclude(pk__in=ORGANIZATION_IDENTITIES)
            .exists(),
            "A local fixture organization exists outside the audited identity set.",
        )

    expected_memberships = {
        UUID("58343c9f-9e45-4449-950c-0ea56e3913c4"): (
            UUID("1b228cb9-becf-4405-9926-437ccb66012e"),
            "POLICE",
            "SUSPENDED",
        ),
        UUID("70c2514e-ca60-4c28-baa3-b6a0063b0e23"): (
            UUID("1b228cb9-becf-4405-9926-437ccb66012e"),
            "POLICE",
            "ACTIVE",
        ),
        UUID("e590263d-03cf-4df7-b1e8-6c2ef7d84ccc"): (
            UUID("637b2520-6b3d-4498-853f-34e38c33e8e9"),
            "HOSPITAL",
            "ACTIVE",
        ),
    }
    for user_id, (organization_id, role, status) in expected_memberships.items():
        rows = list(Membership.objects.using(database).filter(user_id=user_id))
        _fail_if(
            len(rows) != 1
            or rows[0].organization_id != organization_id
            or rows[0].role_group_id != group_ids[role]
            or rows[0].status != status,
            "Fixture organization memberships are incomplete or inconsistent.",
        )
    _fail_if(
        Membership.objects.using(database)
        .filter(user_id=UUID("4e90729d-16f0-406e-a9c9-d59650eb4bf7"))
        .exists(),
        "The generic fixture account has an unexpected organization membership.",
    )
    _fail_if(
        Membership.objects.using(database)
        .filter(organization_id__in=ORGANIZATION_IDENTITIES)
        .count()
        != len(expected_memberships),
        "Managed fixture organizations have unexpected memberships.",
    )
    _fail_if(
        set(
            Group.objects.using(database)
            .get(name=MANAGED_GROUP)
            .user_set.using(database)
            .values_list("pk", flat=True)
        )
        != set(USER_IDENTITIES),
        "The managed fixture group has an ambiguous account set.",
    )

    admin_id = UUID("58343c9f-9e45-4449-950c-0ea56e3913c4")
    source_owner_id = UUID("4bbde553-ddcd-470a-812e-8105b01b47fa")
    _fail_if(
        not source.source_code.startswith("resqvision-local-")
        or source.source_type != "CONTROLLED_FILE"
        or source.owner_organization_id != source_owner_id
        or source.authorization_status != "AUTHORIZED"
        or source.authorized_by_user_id != admin_id
        or source.authorized_at is None
        or source.processing_policy_ref != "local-test-only-processing-v1"
        or source.retention_policy_ref != "local-test-only-retention-v1",
        "The managed fixture source has unexpected state.",
    )
    _fail_if(
        VideoSource.objects.using(database)
        .filter(source_code=SOURCE_CODE)
        .exclude(pk=SOURCE_ID)
        .exists(),
        "The target source identity belongs to another row.",
    )
    _fail_if(
        VideoSource.objects.using(database)
        .filter(
            source_type="CONTROLLED_FILE",
            processing_policy_ref="local-test-only-processing-v1",
            retention_policy_ref="local-test-only-retention-v1",
        )
        .exclude(pk=SOURCE_ID)
        .exists(),
        "A managed local source exists outside the audited identity set.",
    )

    event_times = [FIRST_EVENT_AT + timedelta(minutes=index) for index in range(EVENT_COUNT)]
    events = list(
        DetectionEvent.objects.using(database)
        .filter(
            video_source_id=SOURCE_ID,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            detected_at__in=event_times,
            processing_outcome="OBSERVATION",
        )
        .order_by("detected_at")
    )
    _fail_if(len(events) != EVENT_COUNT, "The fixture detection event set is incomplete.")
    _fail_if(
        set(EVENT_IDS).difference(event.pk for event in events),
        "A known fixture event identity is missing.",
    )

    for number, event in enumerate(events, start=1):
        links = list(CandidateLink.objects.using(database).filter(detection_event_id=event.pk))
        _fail_if(len(links) != 1, "A fixture event has missing or duplicate candidate linkage.")
        candidate = Candidate.objects.using(database).filter(pk=links[0].candidate_id).first()
        _fail_if(
            candidate is None or candidate.status != "VERIFIED",
            "A fixture candidate is not verified.",
        )
        verify_id = _command_ids("verify")[number - 1]
        review_id = _command_ids("review")[number - 1]
        review = CandidateReview.objects.using(database).filter(candidate_id=candidate.pk).first()
        _fail_if(
            review is None
            or review.reviewer_id != admin_id
            or review.decision != "VERIFIED"
            or review.command_id != verify_id
            or CandidateReview.objects.using(database).filter(candidate_id=candidate.pk).count()
            != 1,
            "A fixture candidate review is incomplete or inconsistent.",
        )
        incident = Incident.objects.using(database).filter(candidate_id=candidate.pk).first()
        _fail_if(
            incident is None
            or incident.status != "OPEN"
            or Incident.objects.using(database).filter(candidate_id=candidate.pk).count() != 1
            or IncidentHistory.objects.using(database)
            .filter(
                incident_id=incident.pk,
                from_status__isnull=True,
                to_status="OPEN",
                changed_by_user_id=admin_id,
                command_id=verify_id,
            )
            .count()
            != 1,
            "A fixture incident or its initial history is incomplete.",
        )

        _require_audit(
            AuditEvent,
            action="DETECTION_EVENT_ACCEPTED",
            resource_type="DETECTION_EVENT",
            resource_id=event.pk,
        )
        _require_audit(
            AuditEvent,
            action="CANDIDATE_CREATED",
            resource_type="CANDIDATE",
            resource_id=candidate.pk,
        )
        _require_audit(
            AuditEvent,
            action="CANDIDATE_REVIEW_STARTED",
            resource_type="CANDIDATE",
            resource_id=candidate.pk,
            command_id=review_id,
        )
        _require_audit(
            AuditEvent,
            action="CANDIDATE_VERIFIED",
            resource_type="CANDIDATE",
            resource_id=candidate.pk,
            command_id=verify_id,
        )

        assignments = list(Assignment.objects.using(database).filter(incident_id=incident.pk))
        _fail_if(len(assignments) != 2, "A fixture incident has an incomplete assignment set.")
        expected_assignment_ids = {
            uuid5(NAMESPACE, f"assignment-{target}{'' if number == 1 else f'-{number:03d}'}"): (
                organization_id
            )
            for target, organization_id in zip(
                ("police", "hospital"),
                list(ORGANIZATION_IDENTITIES)[:2],
                strict=True,
            )
        }
        _fail_if(
            {assignment.creation_command_id for assignment in assignments}
            != set(expected_assignment_ids),
            "A fixture assignment has an unexpected command identity.",
        )
        for assignment in assignments:
            _fail_if(
                assignment.target_organization_id
                != expected_assignment_ids[assignment.creation_command_id]
                or assignment.assigned_by_user_id != admin_id
                or assignment.status != "PENDING"
                or assignment.replacement_for_id is not None
                or AssignmentHistory.objects.using(database)
                .filter(
                    response_assignment_id=assignment.pk,
                    from_status__isnull=True,
                    to_status="PENDING",
                    changed_by_user_id=admin_id,
                    command_id=assignment.creation_command_id,
                )
                .count()
                != 1,
                "A fixture assignment or its initial history is inconsistent.",
            )
            _require_audit(
                AuditEvent,
                action="ASSIGNMENT_CREATED",
                resource_type="ASSIGNMENT",
                resource_id=assignment.pk,
                command_id=assignment.creation_command_id,
            )

    _require_audit(
        AuditEvent,
        action="VIDEO_SOURCE_REGISTERED",
        resource_type="VIDEO_SOURCE",
        resource_id=SOURCE_ID,
    )
    _require_audit(
        AuditEvent,
        action="VIDEO_SOURCE_AUTHORIZED",
        resource_type="VIDEO_SOURCE",
        resource_id=SOURCE_ID,
    )

    snapshots = []
    for user_id, target in USER_IDENTITIES.items():
        snapshots.append(("user", user_id, users[user_id].email, target))
    for organization_id, (target, _kind) in ORGANIZATION_IDENTITIES.items():
        snapshots.append(
            ("organization", organization_id, organizations[organization_id].code, target)
        )
    snapshots.append(("source", SOURCE_ID, source.source_code, SOURCE_CODE))
    quote = schema_editor.connection.ops.quote_name
    schema_editor.execute(
        f"CREATE TABLE {quote(ROLLBACK_TABLE)} ("
        "entity_type varchar(16) NOT NULL, "
        "entity_id uuid NOT NULL, "
        "prior_value varchar(254) NOT NULL, "
        "target_value varchar(254) NOT NULL, "
        "PRIMARY KEY (entity_type, entity_id))"
    )
    with schema_editor.connection.cursor() as cursor:
        cursor.executemany(
            f"INSERT INTO {quote(ROLLBACK_TABLE)} "
            "(entity_type, entity_id, prior_value, target_value) VALUES (%s, %s, %s, %s)",
            snapshots,
        )

    for user_id, target in USER_IDENTITIES.items():
        User.objects.using(database).filter(pk=user_id).update(email=target)
    for organization_id, (target, _kind) in ORGANIZATION_IDENTITIES.items():
        Organization.objects.using(database).filter(pk=organization_id).update(code=target)
    VideoSource.objects.using(database).filter(pk=SOURCE_ID).update(source_code=SOURCE_CODE)


def restore_identity_values(apps, schema_editor):
    database = schema_editor.connection.alias
    User = apps.get_model("accounts", "User")
    Organization = apps.get_model("organizations", "Organization")
    VideoSource = apps.get_model("sources", "VideoSource")
    quote = schema_editor.connection.ops.quote_name
    if ROLLBACK_TABLE not in schema_editor.connection.introspection.table_names():
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"SELECT entity_type, entity_id, prior_value, target_value FROM {quote(ROLLBACK_TABLE)}"
        )
        snapshots = cursor.fetchall()
    if not snapshots:
        schema_editor.execute(f"DROP TABLE {quote(ROLLBACK_TABLE)}")
        return
    _fail_if(len(snapshots) != 8, "Fixture identity rollback snapshot is incomplete.")

    values = {
        (entity_type, entity_id): (prior_value, target_value)
        for entity_type, entity_id, prior_value, target_value in snapshots
    }
    for user_id, target in USER_IDENTITIES.items():
        row = values.get(("user", user_id))
        user = User.objects.using(database).filter(pk=user_id).first()
        _fail_if(
            row is None or row[1] != target or user is None or user.email != target,
            "A managed account changed after identity reconciliation; rollback stopped.",
        )
        _fail_if(
            User.objects.using(database).filter(email=row[0]).exclude(pk=user_id).exists(),
            "A prior account identity is now in use; rollback stopped.",
        )
    for organization_id, (target, _kind) in ORGANIZATION_IDENTITIES.items():
        row = values.get(("organization", organization_id))
        organization = Organization.objects.using(database).filter(pk=organization_id).first()
        _fail_if(
            row is None or row[1] != target or organization is None or organization.code != target,
            "A managed organization changed after identity reconciliation; rollback stopped.",
        )
        _fail_if(
            Organization.objects.using(database)
            .filter(code=row[0])
            .exclude(pk=organization_id)
            .exists(),
            "A prior organization identity is now in use; rollback stopped.",
        )
    source_row = values.get(("source", SOURCE_ID))
    source = VideoSource.objects.using(database).filter(pk=SOURCE_ID).first()
    _fail_if(
        source_row is None
        or source_row[1] != SOURCE_CODE
        or source is None
        or source.source_code != SOURCE_CODE,
        "The managed source changed after identity reconciliation; rollback stopped.",
    )
    _fail_if(
        VideoSource.objects.using(database)
        .filter(source_code=source_row[0])
        .exclude(pk=SOURCE_ID)
        .exists(),
        "The prior source identity is now in use; rollback stopped.",
    )

    for user_id in USER_IDENTITIES:
        User.objects.using(database).filter(pk=user_id).update(email=values[("user", user_id)][0])
    for organization_id in ORGANIZATION_IDENTITIES:
        Organization.objects.using(database).filter(pk=organization_id).update(
            code=values[("organization", organization_id)][0]
        )
    VideoSource.objects.using(database).filter(pk=SOURCE_ID).update(source_code=source_row[0])
    schema_editor.execute(f"DROP TABLE {quote(ROLLBACK_TABLE)}")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_seed_role_groups"),
        ("audit", "0001_initial"),
        ("detection", "0001_initial"),
        ("incidents", "0002_remove_candidatereview_ck_review_rationale_and_more"),
        ("organizations", "0001_initial"),
        ("responses", "0003_alter_responseassignment_replacement_for_and_more"),
        ("sources", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(reconcile_identity_values, restore_identity_values),
    ]
