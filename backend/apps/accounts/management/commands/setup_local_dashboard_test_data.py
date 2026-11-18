"""Create reserved, local-only data for live Flutter dashboard verification."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.accounts.models import User
from apps.detection.models import EventProcessingOutcome
from apps.detection.services import DetectionEventCommand, ingest_detection_event
from apps.incidents.models import CandidateStatus, IncidentStatus
from apps.incidents.services import begin_candidate_review, create_candidate, verify_candidate
from apps.organizations.models import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
)
from apps.responses.models import AssignmentStatus
from apps.responses.services import create_assignment
from apps.sources.models import VideoSource, VideoSourceAuthorizationStatus, VideoSourceType
from apps.sources.services.registry import authorize_video_source, register_video_source
from common.domain.actors import HumanActor, MachineActor
from common.domain.authorization import AI_SERVICE_REF

OPT_IN_VARIABLE = "RESQVISION_LOCAL_TEST_DATA_OPT_IN"
MANAGED_GROUP = "RESQVISION_LOCAL_INTEGRATION_TEST"
EMAIL_VARIABLES = {
    "generic": ("RESQVISION_TEST_EMAIL", "RESQVISION_TEST_PASSWORD", None),
    "admin": ("RESQVISION_TEST_ADMIN_EMAIL", "RESQVISION_TEST_ADMIN_PASSWORD", "ADMIN"),
    "police": ("RESQVISION_TEST_POLICE_EMAIL", "RESQVISION_TEST_POLICE_PASSWORD", "POLICE"),
    "hospital": (
        "RESQVISION_TEST_HOSPITAL_EMAIL",
        "RESQVISION_TEST_HOSPITAL_PASSWORD",
        "HOSPITAL",
    ),
}
FIXTURE_NAMESPACE = UUID("879c61e8-97e7-4f2f-9d92-a55009dd835d")
FIXTURE_EVENT_PREFIX = "resqvision-phase5c-assigned-incident-"
FIXTURE_SOURCE_CODE = "resqvision-local-phase5c-source"
FIXTURE_INCIDENT_COUNT = 6


class _LocalFixturePolicy:
    """Narrow command-only policy; never configured for API or production use."""

    _OPERATIONS = frozenset(
        {
            "source.register",
            "source.authorize",
            "candidate.review",
            "candidate.verify",
            "assignment.create",
        }
    )

    def __init__(self, allowed_user_id):
        self._allowed_user_id = allowed_user_id

    def authorize(self, operation, actor, resource=None):
        del resource
        return (
            operation in self._OPERATIONS
            and isinstance(actor, HumanActor)
            and actor.user_id == self._allowed_user_id
        )


class Command(BaseCommand):
    help = "Create idempotent local-only Phase 5C dashboard integration records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rotate-managed-test-passwords",
            action="store_true",
            help=(
                "Explicitly replace credentials only for already-marked .test fixture users."
            ),
        )

    def handle(self, *args, **options):
        del args
        self._require_opt_in()
        self._require_local_database()
        accounts = self._read_accounts()
        self._validate_distinct_emails(accounts)

        with transaction.atomic():
            managed_group = self._get_managed_group()
            role_groups = self._get_role_groups()
            users = {
                key: self._get_or_create_user(
                    email=email,
                    password=password,
                    expected_role=role,
                    managed_group=managed_group,
                    role_groups=role_groups,
                    rotate=options["rotate_managed_test_passwords"],
                )
                for key, (email, password, role) in accounts.items()
            }
            organizations = self._get_test_organizations()
            self._validate_or_create_memberships(
                users=users,
                role_groups=role_groups,
                organizations=organizations,
            )
            incident, assignments = self._get_test_incident_and_assignments(
                admin=users["admin"], organizations=organizations
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Local dashboard test data is ready: 4 managed .test users, "
                "2 operational organizations, 2 active memberships, 1 suspended membership, "
                "1 source, 6 detection events, 6 verified OPEN incidents, "
                "and 12 independent PENDING assignments."
            )
        )
        del incident, assignments

    def _require_local_database(self):
        if not settings.DEBUG:
            raise CommandError("Refusing local test-data setup unless DEBUG=True.")
        database = settings.DATABASES.get("default", {})
        if database.get("ENGINE") != "django.db.backends.postgresql":
            raise CommandError("Refusing local test-data setup without PostgreSQL.")
        if database.get("NAME") != "resqvision_dev":
            raise CommandError("Refusing local test-data setup outside resqvision_dev.")
        host = str(database.get("HOST", "")).strip().lower()
        if host not in {"localhost", "127.0.0.1", "::1", "[::1]"}:
            raise CommandError("Refusing local test-data setup for a non-loopback database host.")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database()")
                connected_name = cursor.fetchone()[0]
        except Exception as exc:
            raise CommandError("Could not verify the connected PostgreSQL database.") from exc
        if connected_name != "resqvision_dev":
            raise CommandError("Refusing local test-data setup outside resqvision_dev.")

    def _require_opt_in(self):
        import os

        if os.environ.get(OPT_IN_VARIABLE) != "1":
            raise CommandError(
                f"Set {OPT_IN_VARIABLE}=1 explicitly to opt in to local fixture creation."
            )

    def _read_accounts(self):
        import os

        accounts = {}
        for key, (email_name, password_name, role) in EMAIL_VARIABLES.items():
            email = os.environ.get(email_name, "").strip().lower()
            password = os.environ.get(password_name, "")
            if not email or not password:
                raise CommandError(
                    f"Both {email_name} and {password_name} must be set; values are not displayed."
                )
            domain = email.rpartition("@")[2]
            if not domain.endswith(".test"):
                raise CommandError(f"{email_name} must use a reserved .test domain.")
            try:
                validate_password(password, user=User(email=email))
            except DjangoValidationError as exc:
                raise CommandError(
                    f"{password_name} does not meet the local test password policy."
                ) from exc
            accounts[key] = (email, password, role)
        return accounts

    def _validate_distinct_emails(self, accounts):
        normalized = [record[0] for record in accounts.values()]
        if len(set(normalized)) != len(normalized):
            raise CommandError("Each live integration identity must have a distinct email.")

    def _get_managed_group(self):
        group, _ = Group.objects.get_or_create(name=MANAGED_GROUP)
        if group.permissions.exists():
            raise CommandError("The local fixture marker group must not carry permissions.")
        return group

    def _get_role_groups(self):
        try:
            groups = {
                name: Group.objects.get(name=name)
                for name in ("ADMIN", "POLICE", "HOSPITAL")
            }
        except Group.DoesNotExist as exc:
            raise CommandError(
                "Role groups are missing; apply the project migrations first."
            ) from exc
        if any(group.permissions.exists() for group in groups.values()):
            raise CommandError("Role groups must not grant permissions to fixture users.")
        return groups

    def _get_or_create_user(
        self,
        *,
        email,
        password,
        expected_role,
        managed_group,
        role_groups,
        rotate,
    ):
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(email=email, password=password)
            user.groups.add(managed_group)
            if expected_role:
                user.groups.add(role_groups[expected_role])
            return user

        if not email.rpartition("@")[2].endswith(".test"):
            raise CommandError("Refusing to use an existing non-test account.")
        if not user.groups.filter(pk=managed_group.pk).exists():
            raise CommandError(
                "An account with a configured fixture email exists but is not marked as managed."
            )
        if not user.is_active or user.is_staff or user.is_superuser:
            raise CommandError("A managed fixture user has unexpected account privileges/state.")
        expected_groups = {managed_group.pk}
        if expected_role:
            expected_groups.add(role_groups[expected_role].pk)
        if set(user.groups.values_list("pk", flat=True)) != expected_groups:
            raise CommandError("A managed fixture user has unexpected role groups.")
        if user.user_permissions.exists():
            raise CommandError("A managed fixture user has unexpected direct permissions.")
        if not user.check_password(password):
            if not rotate:
                raise CommandError(
                    "A managed fixture account has a different password; use the explicit "
                    "--rotate-managed-test-passwords option to replace it."
                )
            user.set_password(password)
            user.save(update_fields=["password"])
        return user

    def _get_test_organizations(self):
        specifications = (
            ("resqvision-local-phase5c-police", "ResQVision Local Phase 5C Police", "POLICE"),
            (
                "resqvision-local-phase5c-hospital",
                "ResQVision Local Phase 5C Hospital",
                "HOSPITAL",
            ),
            (
                "resqvision-local-phase5c-source-owner",
                "ResQVision Local Phase 5C Source Owner",
                "SOURCE_OWNER",
            ),
        )
        organizations = {}
        for code, display_name, kind in specifications:
            organization = Organization.objects.filter(code=code).first()
            if organization is None:
                organization = Organization.objects.create(
                    code=code,
                    display_name=display_name,
                    organization_kind=kind,
                )
            elif (
                organization.display_name != display_name
                or organization.organization_kind != kind
                or not organization.is_active
            ):
                raise CommandError(
                    "A reserved local fixture organization code exists with different data."
                )
            organizations[kind] = organization
        return organizations

    def _validate_or_create_memberships(self, *, users, role_groups, organizations):
        expected = {
            "police": (organizations["POLICE"], role_groups["POLICE"]),
            "hospital": (organizations["HOSPITAL"], role_groups["HOSPITAL"]),
        }
        for key, user in users.items():
            existing = list(OrganizationMembership.objects.filter(user=user))
            if key == "admin":
                inactive_scope = (organizations["POLICE"], role_groups["POLICE"])
                if len(existing) > 1 or any(
                    item.organization_id != inactive_scope[0].pk
                    or item.role_group_id != inactive_scope[1].pk
                    or item.status != MembershipStatus.SUSPENDED
                    for item in existing
                ):
                    raise CommandError(
                        "The Admin fixture may have only its reserved suspended Police membership."
                    )
                if not existing:
                    membership = OrganizationMembership(
                        user=user,
                        organization=inactive_scope[0],
                        role_group=inactive_scope[1],
                        status=MembershipStatus.SUSPENDED,
                    )
                    membership.full_clean()
                    membership.save()
                continue
            if key not in expected:
                if existing:
                    raise CommandError(
                        "The generic auth fixture user must not have memberships."
                    )
                continue
            organization, role_group = expected[key]
            if len(existing) > 1 or any(
                item.organization_id != organization.pk
                or item.role_group_id != role_group.pk
                or item.status != MembershipStatus.ACTIVE
                for item in existing
            ):
                raise CommandError(
                    "A managed operational user has unexpected organization memberships."
                )
            if not existing:
                membership = OrganizationMembership(
                    user=user,
                    organization=organization,
                    role_group=role_group,
                    status=MembershipStatus.ACTIVE,
                )
                membership.full_clean()
                membership.save()

    def _get_test_incident_and_assignments(self, *, admin, organizations):
        actor = HumanActor(admin)
        policy = _LocalFixturePolicy(admin.pk)
        owner = organizations["SOURCE_OWNER"]
        source = VideoSource.objects.filter(source_code=FIXTURE_SOURCE_CODE).first()
        if source is None:
            source = register_video_source(
                actor=actor,
                source_code=FIXTURE_SOURCE_CODE,
                name="ResQVision Local Phase 5C Controlled Fixture",
                source_type=VideoSourceType.CONTROLLED_FILE,
                processing_policy_ref="local-test-only-processing-v1",
                retention_policy_ref="local-test-only-retention-v1",
                owner_organization_id=owner.pk,
                policy=policy,
            )
            source = authorize_video_source(
                source_id=source.pk,
                actor=actor,
                authorization_reference="LOCAL-TEST-ONLY-PHASE5C",
                policy=policy,
            )
        elif (
            source.name != "ResQVision Local Phase 5C Controlled Fixture"
            or source.source_type != VideoSourceType.CONTROLLED_FILE
            or source.owner_organization_id != owner.pk
            or source.processing_policy_ref != "local-test-only-processing-v1"
            or source.retention_policy_ref != "local-test-only-retention-v1"
            or source.authorization_status != VideoSourceAuthorizationStatus.AUTHORIZED
            or source.authorized_by_user_id != admin.pk
            or source.authorization_reference != "LOCAL-TEST-ONLY-PHASE5C"
        ):
            raise CommandError("The reserved test source exists with unexpected state.")

        incidents = []
        assignments = []
        for incident_number in range(1, FIXTURE_INCIDENT_COUNT + 1):
            command_suffix = "" if incident_number == 1 else f"-{incident_number:03d}"
            event = ingest_detection_event(
                DetectionEventCommand(
                    video_source_id=source.pk,
                    external_event_id=(
                        f"{FIXTURE_EVENT_PREFIX}{incident_number:03d}"
                    ),
                    model_name="resqvision-local-test-model",
                    model_version="1.0-test",
                    detected_at=datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
                    + timedelta(minutes=incident_number - 1),
                    processing_outcome=EventProcessingOutcome.OBSERVATION,
                    actor=MachineActor(AI_SERVICE_REF),
                    auxiliary_metadata={"fixture": "local_phase5c"},
                )
            )
            candidate = create_candidate(
                detection_event_id=event.pk,
                actor=MachineActor(AI_SERVICE_REF),
            )
            if candidate.status == CandidateStatus.RECEIVED:
                begin_candidate_review(
                    candidate_id=candidate.pk,
                    actor=actor,
                    command_id=uuid5(
                        FIXTURE_NAMESPACE,
                        f"candidate-review{command_suffix}",
                    ),
                    policy=policy,
                )
            incident_result = verify_candidate(
                candidate_id=candidate.pk,
                actor=actor,
                command_id=uuid5(
                    FIXTURE_NAMESPACE,
                    f"candidate-verify{command_suffix}",
                ),
                rationale="Verified controlled local Phase 5C dashboard fixture.",
                policy=policy,
            )
            incident = incident_result.value
            if incident.status != IncidentStatus.OPEN:
                raise CommandError(
                    "A reserved test incident is not in the expected OPEN state."
                )
            incidents.append(incident)

            for kind in ("POLICE", "HOSPITAL"):
                assignment_result = create_assignment(
                    incident_id=incident.pk,
                    target_organization_id=organizations[kind].pk,
                    actor=actor,
                    command_id=uuid5(
                        FIXTURE_NAMESPACE,
                        f"assignment-{kind.lower()}{command_suffix}",
                    ),
                    policy=policy,
                )
                if assignment_result.value.status != AssignmentStatus.PENDING:
                    raise CommandError(
                        "A reserved local fixture assignment is not in the expected PENDING state."
                    )
                assignments.append(assignment_result.value)

        return incidents, assignments
