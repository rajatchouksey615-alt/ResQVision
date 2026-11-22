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
from apps.audit.models import AuditEvent
from apps.detection.models import DetectionEvent, EventProcessingOutcome
from apps.detection.services import DetectionEventCommand, ingest_detection_event
from apps.incidents.models import (
    AccidentCandidate,
    AccidentIncident,
    CandidateDetectionEvent,
    CandidateReview,
    CandidateStatus,
    IncidentStatus,
    IncidentStatusHistory,
)
from apps.incidents.services import begin_candidate_review, create_candidate, verify_candidate
from apps.organizations.models import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
)
from apps.responses.models import AssignmentStatus, AssignmentStatusHistory, ResponseAssignment
from apps.responses.services import create_assignment
from apps.sources.models import (
    VideoSource,
    VideoSourceAuthorizationStatus,
    VideoSourceAvailabilityStatus,
    VideoSourceType,
)
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
FIXTURE_ACCOUNT_IDS = (
    UUID("4e90729d-16f0-406e-a9c9-d59650eb4bf7"),
    UUID("58343c9f-9e45-4449-950c-0ea56e3913c4"),
    UUID("70c2514e-ca60-4c28-baa3-b6a0063b0e23"),
    UUID("e590263d-03cf-4df7-b1e8-6c2ef7d84ccc"),
)
FIXTURE_ORGANIZATION_IDS = (
    UUID("1b228cb9-becf-4405-9926-437ccb66012e"),
    UUID("637b2520-6b3d-4498-853f-34e38c33e8e9"),
    UUID("4bbde553-ddcd-470a-812e-8105b01b47fa"),
)
FIXTURE_SOURCE_ID = UUID("b745b497-19f7-4171-bdeb-c8101a2be8d2")
FIXTURE_EVENT_IDS = (
    UUID("93e4f978-28fb-44c1-8e49-a2a34342da16"),
    UUID("d2b331aa-ebcb-435b-98b8-96b728b2952d"),
    UUID("c469d07e-067d-47cd-8558-376d085a704d"),
    UUID("dfc42a1d-27d8-4c3e-824f-1e6271787ee5"),
    UUID("b938f344-5ceb-4e55-b2c1-3078e1bbdc4f"),
    UUID("66ae1a97-2930-4375-970d-6ca1c9e0f53d"),
)
# These values are persistent machine identities. Keep them separate from display labels.
FIXTURE_ORGANIZATION_CODES = {
    "POLICE": "resqvision-local-dashboard-police",
    "HOSPITAL": "resqvision-local-dashboard-hospital",
    "SOURCE_OWNER": "resqvision-local-dashboard-source-owner",
}
FIXTURE_ORGANIZATION_NAMES = {
    "POLICE": "ResQVision Local Dashboard Police",
    "HOSPITAL": "ResQVision Local Dashboard Hospital",
    "SOURCE_OWNER": "ResQVision Local Dashboard Source Owner",
}
FIXTURE_EVENT_PREFIX = "resqvision-dashboard-assigned-incident-"
FIXTURE_SOURCE_CODE = "resqvision-local-dashboard-source"
FIXTURE_SOURCE_NAME = "ResQVision Local Dashboard Controlled Fixture"
FIXTURE_SOURCE_AUTHORIZATION_REFERENCE = "LOCAL-TEST-ONLY-DASHBOARD"
FIXTURE_MODEL_NAME = "resqvision-local-test-model"
FIXTURE_MODEL_VERSION = "1.0-test"
FIXTURE_FIRST_EVENT_AT = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
FIXTURE_EVENT_METADATA = {"fixture": "local_dashboard"}
FIXTURE_VERIFICATION_RATIONALE = "Verified controlled local dashboard fixture."
FIXTURE_INCIDENT_COUNT = 6


class _LocalFixturePolicy:
    """Narrow command-only policy; never configured for API or production use."""

    _OPERATIONS = frozenset(
        {
            "source.register",
            "source.authorize",
            "candidate.create",
            "candidate.review",
            "candidate.verify",
            "assignment.create",
        }
    )

    def __init__(self, allowed_user_id):
        self._allowed_user_id = allowed_user_id

    def authorize(self, operation, actor, resource=None):
        if operation == "candidate.create":
            return (
                isinstance(actor, MachineActor)
                and actor.service_ref == AI_SERVICE_REF
                and isinstance(resource, DetectionEvent)
                and (
                    (
                        resource.video_source_id == FIXTURE_SOURCE_ID
                        and resource.pk in FIXTURE_EVENT_IDS
                    )
                    or (
                        resource.video_source.source_code == FIXTURE_SOURCE_CODE
                        and resource.external_event_id.startswith(FIXTURE_EVENT_PREFIX)
                    )
                )
            )
        return (
            operation in self._OPERATIONS
            and isinstance(actor, HumanActor)
            and actor.user_id == self._allowed_user_id
        )


class Command(BaseCommand):
    help = "Create idempotent local-only dashboard integration records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rotate-managed-test-passwords",
            action="store_true",
            help=("Explicitly replace credentials only for already-marked .test fixture users."),
        )

    def handle(self, *args, **options):
        del args
        self._require_opt_in()
        self._require_local_database()
        accounts = self._read_accounts()
        self._validate_distinct_emails(accounts)

        with transaction.atomic():
            role_groups = self._get_role_groups()
            managed_group = Group.objects.filter(name=MANAGED_GROUP).first()
            if self._has_existing_fixture_footprint(accounts, managed_group):
                self._validate_complete_fixture_reuse(
                    accounts=accounts,
                    managed_group=managed_group,
                    role_groups=role_groups,
                    rotate=options["rotate_managed_test_passwords"],
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        "Complete local dashboard fixture found and reused without writes."
                    )
                )
                return

            managed_group = self._get_managed_group()
            self._assert_managed_account_emails_match(accounts, managed_group)
            self._assert_no_conflicting_organization_codes()
            self._assert_no_conflicting_source_code()
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
            self._assert_existing_membership_codes_match(users)
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

    def _has_existing_fixture_footprint(self, accounts, managed_group):
        if managed_group is not None:
            return True
        if User.objects.filter(pk__in=FIXTURE_ACCOUNT_IDS).exists():
            return True
        if Organization.objects.filter(pk__in=FIXTURE_ORGANIZATION_IDS).exists():
            return True
        if VideoSource.objects.filter(pk=FIXTURE_SOURCE_ID).exists():
            return True
        if DetectionEvent.objects.filter(pk__in=FIXTURE_EVENT_IDS).exists():
            return True
        configured_emails = [email for email, _, _ in accounts.values()]
        if User.objects.filter(email__in=configured_emails).exists():
            return True
        if Organization.objects.filter(code__startswith="resqvision-local-").exists():
            return True
        if VideoSource.objects.filter(
            source_type=VideoSourceType.CONTROLLED_FILE,
            processing_policy_ref="local-test-only-processing-v1",
            retention_policy_ref="local-test-only-retention-v1",
        ).exists():
            return True
        event_times = [
            self._fixture_event_time(number) for number in range(1, FIXTURE_INCIDENT_COUNT + 1)
        ]
        if DetectionEvent.objects.filter(
            model_name=FIXTURE_MODEL_NAME,
            model_version=FIXTURE_MODEL_VERSION,
            detected_at__in=event_times,
        ).exists():
            return True
        if CandidateReview.objects.filter(command_id__in=self._verification_command_ids()).exists():
            return True
        if ResponseAssignment.objects.filter(
            creation_command_id__in=self._assignment_command_ids()
        ).exists():
            return True
        audit_resource_ids = (
            *FIXTURE_ACCOUNT_IDS,
            *FIXTURE_ORGANIZATION_IDS,
            FIXTURE_SOURCE_ID,
            *FIXTURE_EVENT_IDS,
        )
        if AuditEvent.objects.filter(resource_id__in=audit_resource_ids).exists():
            return True
        audit_command_ids = [
            str(command_id)
            for command_id in (
                *self._verification_command_ids(),
                *self._review_command_ids(),
                *self._assignment_command_ids(),
            )
        ]
        return AuditEvent.objects.filter(safe_context__command_id__in=audit_command_ids).exists()

    def _validate_complete_fixture_reuse(self, *, accounts, managed_group, role_groups, rotate):
        if managed_group is None:
            raise CommandError(
                "The existing local fixture is incomplete; Refusing to create a replacement "
                "organization or account."
            )
        if rotate:
            raise CommandError(
                "Credential rotation is unavailable while reusing an existing fixture."
            )

        configured_emails = {email for email, _, _ in accounts.values()}
        existing_emails = set(managed_group.user_set.values_list("email", flat=True))
        if existing_emails != configured_emails:
            raise CommandError(
                "The existing local fixture account set is incomplete or ambiguous; "
                "Refusing to create replacement accounts."
            )

        users = {}
        for key, (email, password, expected_role) in accounts.items():
            user = User.objects.filter(email=email).first()
            if user is None:
                raise CommandError("The existing local fixture account set is incomplete.")
            users[key] = self._get_or_create_user(
                email=email,
                password=password,
                expected_role=expected_role,
                managed_group=managed_group,
                role_groups=role_groups,
                rotate=False,
            )

        organizations = {}
        for kind, code in FIXTURE_ORGANIZATION_CODES.items():
            organization = Organization.objects.filter(code=code).first()
            if (
                organization is None
                or organization.organization_kind != kind
                or not organization.is_active
            ):
                raise CommandError(
                    "The existing local fixture organization set is incomplete or ambiguous; "
                    "Refusing to create replacement organizations."
                )
            organizations[kind] = organization

        self._assert_no_conflicting_organization_codes()
        self._assert_no_conflicting_source_code()
        self._assert_existing_membership_codes_match(users)
        self._assert_complete_memberships(users, role_groups, organizations)
        self._assert_complete_domain_fixture(users["admin"], organizations)

    def _assert_complete_memberships(self, users, role_groups, organizations):
        expected = {
            "admin": (organizations["POLICE"], role_groups["POLICE"], MembershipStatus.SUSPENDED),
            "police": (organizations["POLICE"], role_groups["POLICE"], MembershipStatus.ACTIVE),
            "hospital": (
                organizations["HOSPITAL"],
                role_groups["HOSPITAL"],
                MembershipStatus.ACTIVE,
            ),
            "generic": None,
        }
        for key, user in users.items():
            existing = list(OrganizationMembership.objects.filter(user=user))
            expectation = expected[key]
            if expectation is None:
                if existing:
                    raise CommandError("The generic fixture account has unexpected memberships.")
                continue
            organization, role_group, status = expectation
            if len(existing) != 1 or any(
                membership.organization_id != organization.pk
                or membership.role_group_id != role_group.pk
                or membership.status != status
                for membership in existing
            ):
                raise CommandError(
                    "The existing local fixture memberships are incomplete or ambiguous."
                )

    def _assert_complete_domain_fixture(self, admin, organizations):
        source = VideoSource.objects.filter(source_code=FIXTURE_SOURCE_CODE).first()
        if (
            source is None
            or source.source_type != VideoSourceType.CONTROLLED_FILE
            or source.owner_organization_id != organizations["SOURCE_OWNER"].pk
            or source.processing_policy_ref != "local-test-only-processing-v1"
            or source.retention_policy_ref != "local-test-only-retention-v1"
            or source.authorization_status != VideoSourceAuthorizationStatus.AUTHORIZED
            or source.authorized_by_user_id != admin.pk
            or source.authorized_at is None
        ):
            raise CommandError(
                "The existing local fixture source is incomplete or ambiguous; Refusing to "
                "register a replacement."
            )

        self._require_fixture_audit(
            action="VIDEO_SOURCE_REGISTERED",
            resource_type="VIDEO_SOURCE",
            resource_id=source.pk,
        )
        self._require_fixture_audit(
            action="VIDEO_SOURCE_AUTHORIZED",
            resource_type="VIDEO_SOURCE",
            resource_id=source.pk,
        )

        expected_event_times = [
            self._fixture_event_time(number) for number in range(1, FIXTURE_INCIDENT_COUNT + 1)
        ]
        if (
            DetectionEvent.objects.filter(
                video_source=source,
                model_name=FIXTURE_MODEL_NAME,
                model_version=FIXTURE_MODEL_VERSION,
                detected_at__in=expected_event_times,
                processing_outcome=EventProcessingOutcome.OBSERVATION,
            ).count()
            != FIXTURE_INCIDENT_COUNT
        ):
            raise CommandError("The existing local fixture event set is ambiguous.")

        for number in range(1, FIXTURE_INCIDENT_COUNT + 1):
            event = DetectionEvent.objects.filter(
                video_source=source,
                model_name=FIXTURE_MODEL_NAME,
                model_version=FIXTURE_MODEL_VERSION,
                detected_at=self._fixture_event_time(number),
                processing_outcome=EventProcessingOutcome.OBSERVATION,
            ).first()
            if (
                event is None
                or DetectionEvent.objects.filter(
                    video_source=source,
                    model_name=FIXTURE_MODEL_NAME,
                    model_version=FIXTURE_MODEL_VERSION,
                    detected_at=self._fixture_event_time(number),
                    processing_outcome=EventProcessingOutcome.OBSERVATION,
                ).count()
                != 1
            ):
                raise CommandError("The existing local fixture event set is incomplete.")
            self._require_fixture_audit(
                action="DETECTION_EVENT_ACCEPTED",
                resource_type="DETECTION_EVENT",
                resource_id=event.pk,
            )

            links = list(CandidateDetectionEvent.objects.filter(detection_event=event))
            if len(links) != 1:
                raise CommandError("An existing fixture event has missing or duplicate linkage.")
            candidate = AccidentCandidate.objects.filter(pk=links[0].candidate_id).first()
            if candidate is None or candidate.status != CandidateStatus.VERIFIED:
                raise CommandError("An existing fixture candidate is not verified.")
            self._require_fixture_audit(
                action="CANDIDATE_CREATED",
                resource_type="CANDIDATE",
                resource_id=candidate.pk,
            )
            command_suffix = "" if number == 1 else f"-{number:03d}"
            review_command_id = uuid5(FIXTURE_NAMESPACE, f"candidate-review{command_suffix}")
            verify_command_id = uuid5(FIXTURE_NAMESPACE, f"candidate-verify{command_suffix}")
            review = CandidateReview.objects.filter(candidate=candidate).first()
            if (
                review is None
                or review.reviewer_id != admin.pk
                or review.decision != "VERIFIED"
                or review.command_id != verify_command_id
                or CandidateReview.objects.filter(candidate=candidate).count() != 1
            ):
                raise CommandError("An existing fixture review is incomplete or ambiguous.")
            self._require_fixture_audit(
                action="CANDIDATE_REVIEW_STARTED",
                resource_type="CANDIDATE",
                resource_id=candidate.pk,
                command_id=review_command_id,
            )
            self._require_fixture_audit(
                action="CANDIDATE_VERIFIED",
                resource_type="CANDIDATE",
                resource_id=candidate.pk,
                command_id=verify_command_id,
            )

            incident = AccidentIncident.objects.filter(candidate=candidate).first()
            if (
                incident is None
                or incident.status != IncidentStatus.OPEN
                or AccidentIncident.objects.filter(candidate=candidate).count() != 1
                or IncidentStatusHistory.objects.filter(
                    incident=incident,
                    from_status__isnull=True,
                    to_status=IncidentStatus.OPEN,
                    changed_by_user=admin,
                    command_id=verify_command_id,
                ).count()
                != 1
            ):
                raise CommandError("An existing fixture incident is incomplete or ambiguous.")

            expected_assignments = {}
            for kind in ("POLICE", "HOSPITAL"):
                assignment_command_id = uuid5(
                    FIXTURE_NAMESPACE,
                    f"assignment-{kind.lower()}{command_suffix}",
                )
                expected_assignments[assignment_command_id] = organizations[kind]
            assignments = list(ResponseAssignment.objects.filter(incident=incident))
            if len(assignments) != 2:
                raise CommandError("An existing fixture assignment set is incomplete.")
            for assignment in assignments:
                target = expected_assignments.get(assignment.creation_command_id)
                if (
                    target is None
                    or assignment.target_organization_id != target.pk
                    or assignment.assigned_by_user_id != admin.pk
                    or assignment.status != AssignmentStatus.PENDING
                    or assignment.replacement_for_id is not None
                    or AssignmentStatusHistory.objects.filter(
                        response_assignment=assignment,
                        from_status__isnull=True,
                        to_status=AssignmentStatus.PENDING,
                        changed_by_user=admin,
                        command_id=assignment.creation_command_id,
                    ).count()
                    != 1
                ):
                    raise CommandError("An existing fixture assignment is incomplete.")
                self._require_fixture_audit(
                    action="ASSIGNMENT_CREATED",
                    resource_type="ASSIGNMENT",
                    resource_id=assignment.pk,
                    command_id=assignment.creation_command_id,
                )

    @staticmethod
    def _require_fixture_audit(*, action, resource_type, resource_id, command_id=None):
        events = AuditEvent.objects.filter(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=AuditEvent.Outcome.SUCCESS,
        )
        if command_id is not None:
            events = events.filter(safe_context__command_id=str(command_id))
        if not events.exists():
            raise CommandError("The existing local fixture audit history is incomplete.")

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
                name: Group.objects.get(name=name) for name in ("ADMIN", "POLICE", "HOSPITAL")
            }
        except Group.DoesNotExist as exc:
            raise CommandError(
                "Role groups are missing; apply the project migrations first."
            ) from exc
        if any(group.permissions.exists() for group in groups.values()):
            raise CommandError("Role groups must not grant permissions to fixture users.")
        return groups

    def _assert_managed_account_emails_match(self, accounts, managed_group):
        configured_emails = {email for email, _, _ in accounts.values()}
        existing_emails = set(managed_group.user_set.values_list("email", flat=True))
        prior_review_command_ids = []
        for number in range(1, FIXTURE_INCIDENT_COUNT + 1):
            command_suffix = "" if number == 1 else f"-{number:03d}"
            prior_review_command_ids.append(
                uuid5(FIXTURE_NAMESPACE, f"candidate-verify{command_suffix}")
            )
        prior_fixture_reviews_exist = CandidateReview.objects.filter(
            command_id__in=prior_review_command_ids
        ).exists()
        if prior_fixture_reviews_exist and existing_emails != configured_emails:
            raise CommandError(
                "Existing local fixture review history does not match the configured managed "
                "account identities. Refusing to create replacement accounts; reconcile the "
                "fixture data explicitly."
            )
        if existing_emails.difference(configured_emails):
            raise CommandError(
                "Managed local fixture accounts already use different email identifiers. "
                "Refusing to create replacement accounts; configure the existing account pairs "
                "or reconcile the fixture data explicitly."
            )

    def _assert_existing_membership_codes_match(self, users):
        expected_kinds = {
            "admin": "POLICE",
            "police": "POLICE",
            "hospital": "HOSPITAL",
        }
        for key, user in users.items():
            memberships = OrganizationMembership.objects.filter(user=user).select_related(
                "organization"
            )
            if key not in expected_kinds:
                if memberships.exists():
                    raise CommandError(
                        "The generic local fixture account has an unexpected organization link."
                    )
                continue
            expected_kind = expected_kinds[key]
            expected_code = FIXTURE_ORGANIZATION_CODES[expected_kind]
            if any(
                membership.organization.organization_kind != expected_kind
                or membership.organization.code != expected_code
                for membership in memberships
            ):
                raise CommandError(
                    "A managed local fixture account is linked to a different organization "
                    "identifier. Refusing to create replacement organizations; reconcile the "
                    "fixture data explicitly."
                )

    def _assert_no_conflicting_organization_codes(self):
        for kind, code in FIXTURE_ORGANIZATION_CODES.items():
            existing_local_organizations = Organization.objects.filter(
                organization_kind=kind,
                code__startswith="resqvision-local-",
            ).exclude(code=code)
            if existing_local_organizations.exists():
                raise CommandError(
                    "A local fixture organization exists under a different code. "
                    "Refusing to create a replacement organization; reconcile the fixture "
                    "data explicitly."
                )

    def _assert_no_conflicting_source_code(self):
        existing_local_sources = VideoSource.objects.filter(
            source_type=VideoSourceType.CONTROLLED_FILE,
            processing_policy_ref="local-test-only-processing-v1",
            retention_policy_ref="local-test-only-retention-v1",
        ).exclude(source_code=FIXTURE_SOURCE_CODE)
        if existing_local_sources.exists():
            raise CommandError(
                "A managed local source exists under a different source identifier. "
                "Refusing to register a replacement; reconcile the fixture data explicitly."
            )

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
        organizations = {}
        for kind in ("POLICE", "HOSPITAL", "SOURCE_OWNER"):
            code = FIXTURE_ORGANIZATION_CODES[kind]
            display_name = FIXTURE_ORGANIZATION_NAMES[kind]
            organization = Organization.objects.filter(code=code).first()
            if organization is None:
                self._assert_no_conflicting_organization_codes()
                organization = Organization.objects.create(
                    code=code,
                    display_name=display_name,
                    organization_kind=kind,
                )
            elif organization.organization_kind != kind or not organization.is_active:
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
                    raise CommandError("The generic auth fixture user must not have memberships.")
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
            self._assert_no_conflicting_source_code()
            source = register_video_source(
                actor=actor,
                source_code=FIXTURE_SOURCE_CODE,
                name=FIXTURE_SOURCE_NAME,
                source_type=VideoSourceType.CONTROLLED_FILE,
                processing_policy_ref="local-test-only-processing-v1",
                retention_policy_ref="local-test-only-retention-v1",
                owner_organization_id=owner.pk,
                policy=policy,
            )
            source = authorize_video_source(
                source_id=source.pk,
                actor=actor,
                authorization_reference=FIXTURE_SOURCE_AUTHORIZATION_REFERENCE,
                policy=policy,
            )
            source.availability_status = VideoSourceAvailabilityStatus.AVAILABLE
            source.save(update_fields=["availability_status", "updated_at"])
        elif (
            source.source_type != VideoSourceType.CONTROLLED_FILE
            or source.owner_organization_id != owner.pk
            or source.processing_policy_ref != "local-test-only-processing-v1"
            or source.retention_policy_ref != "local-test-only-retention-v1"
            or source.authorization_status != VideoSourceAuthorizationStatus.AUTHORIZED
            or source.availability_status != VideoSourceAvailabilityStatus.AVAILABLE
            or source.authorized_by_user_id != admin.pk
        ):
            raise CommandError("The reserved test source exists with unexpected state.")

        self._assert_existing_event_identities_match(source)

        incidents = []
        assignments = []
        for incident_number in range(1, FIXTURE_INCIDENT_COUNT + 1):
            command_suffix = "" if incident_number == 1 else f"-{incident_number:03d}"
            event = ingest_detection_event(
                DetectionEventCommand(
                    video_source_id=source.pk,
                    external_event_id=self._fixture_event_id(incident_number),
                    model_name=FIXTURE_MODEL_NAME,
                    model_version=FIXTURE_MODEL_VERSION,
                    detected_at=self._fixture_event_time(incident_number),
                    processing_outcome=EventProcessingOutcome.OBSERVATION,
                    actor=MachineActor(AI_SERVICE_REF),
                    auxiliary_metadata=FIXTURE_EVENT_METADATA.copy(),
                )
            )
            candidate = create_candidate(
                detection_event_id=event.pk,
                actor=MachineActor(AI_SERVICE_REF),
                policy=policy,
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
                rationale=FIXTURE_VERIFICATION_RATIONALE,
                policy=policy,
            )
            incident = incident_result.value
            if incident.status != IncidentStatus.OPEN:
                raise CommandError("A reserved test incident is not in the expected OPEN state.")
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

    def _assert_existing_event_identities_match(self, source):
        for incident_number in range(1, FIXTURE_INCIDENT_COUNT + 1):
            existing_events = DetectionEvent.objects.filter(
                video_source=source,
                model_name=FIXTURE_MODEL_NAME,
                model_version=FIXTURE_MODEL_VERSION,
                detected_at=self._fixture_event_time(incident_number),
                processing_outcome=EventProcessingOutcome.OBSERVATION,
            )
            expected_event_id = self._fixture_event_id(incident_number)
            if any(
                "fixture" in event.auxiliary_metadata
                and (
                    event.external_event_id != expected_event_id
                    or event.auxiliary_metadata != FIXTURE_EVENT_METADATA
                )
                for event in existing_events
            ):
                raise CommandError(
                    "A managed local event exists under different fixture identifiers. "
                    "Refusing to ingest a replacement; reconcile the fixture data explicitly."
                )

    @staticmethod
    def _fixture_event_id(incident_number):
        return f"{FIXTURE_EVENT_PREFIX}{incident_number:03d}"

    @staticmethod
    def _fixture_event_time(incident_number):
        return FIXTURE_FIRST_EVENT_AT + timedelta(minutes=incident_number - 1)

    @staticmethod
    def _verification_command_ids():
        return [
            uuid5(
                FIXTURE_NAMESPACE,
                f"candidate-verify{'' if number == 1 else f'-{number:03d}'}",
            )
            for number in range(1, FIXTURE_INCIDENT_COUNT + 1)
        ]

    @staticmethod
    def _review_command_ids():
        return [
            uuid5(
                FIXTURE_NAMESPACE,
                f"candidate-review{'' if number == 1 else f'-{number:03d}'}",
            )
            for number in range(1, FIXTURE_INCIDENT_COUNT + 1)
        ]

    @staticmethod
    def _assignment_command_ids():
        return [
            uuid5(
                FIXTURE_NAMESPACE,
                f"assignment-{kind.lower()}{'' if number == 1 else f'-{number:03d}'}",
            )
            for number in range(1, FIXTURE_INCIDENT_COUNT + 1)
            for kind in ("POLICE", "HOSPITAL")
        ]
