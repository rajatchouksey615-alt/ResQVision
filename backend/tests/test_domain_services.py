"""PostgreSQL-backed integration tests for the Phase 3 domain commands."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import close_old_connections
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.detection.models import DetectionEvent
from apps.detection.services import DetectionEventCommand, ingest_detection_event
from apps.evidence.models import EvidenceAsset, EvidenceStatus
from apps.evidence.services import (
    EvidenceValidation,
    StorageVerification,
    authorize_upload_session,
    complete_upload,
    create_evidence_asset,
    create_upload_session,
    expire_evidence,
    mark_evidence_available,
    mark_evidence_deleted,
    record_evidence_access,
    validate_evidence,
)
from apps.incidents.models import (
    AccidentIncident,
    CandidateDetectionEvent,
    CandidateReview,
    CandidateStatus,
    IncidentStatus,
    IncidentStatusHistory,
)
from apps.incidents.services import (
    associate_detection_event,
    begin_candidate_review,
    close_incident,
    create_candidate,
    reject_candidate,
    resolve_incident,
    verify_candidate,
)
from apps.locations.models import LocationCorrectionHistory, LocationRecord
from apps.locations.services import (
    correct_location_claim,
    create_location_claim,
    get_current_location_claim,
    verify_location_claim,
)
from apps.notifications.models import Notification, NotificationDeliveryAttempt
from apps.notifications.services import (
    create_notification,
    mark_notification_pending,
    mark_notification_read,
    record_delivery_failure,
    record_simulated_delivery,
)
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.services import suspend_membership, validate_organization_membership
from apps.responses.models import (
    AssignmentStatus,
    AssignmentStatusHistory,
    Response,
    ResponseActivityKind,
    ResponseAssignment,
)
from apps.responses.services import (
    acknowledge_assignment,
    create_assignment,
    reassign_assignment,
    start_response,
)
from apps.sources.models import VideoSource, VideoSourceAuthorizationStatus
from apps.sources.services import authorize_video_source, register_video_source
from common.domain.actors import HumanActor, MachineActor
from common.domain.exceptions import (
    AuthorizationDenied,
    BusinessRuleViolation,
    IdempotencyConflict,
    InvalidStateTransition,
    PolicyNotConfigured,
    ResourceNotFound,
)


class AllowPolicy:
    def __init__(self, *allowed_operations: str):
        self.allowed_operations = frozenset(allowed_operations)

    def authorize(self, operation, actor, resource=None) -> bool:
        return operation in self.allowed_operations


def allow(*operations: str) -> AllowPolicy:
    return AllowPolicy(*operations)


def ai_event_command(source: VideoSource, *, external_id: str, version: str = "1.0.0"):
    return DetectionEventCommand(
        video_source_id=source.pk,
        external_event_id=external_id,
        model_name="resqvision-test-detector",
        model_version=version,
        detected_at=timezone.now(),
        processing_outcome=DetectionEvent.ProcessingOutcome.OBSERVATION,
        actor=MachineActor("AI_SERVICE"),
        confidence=Decimal("0.8500"),
        auxiliary_metadata={"schema": 1},
    )


def authorize_fixture_source(source: VideoSource, user) -> VideoSource:
    source.authorization_status = VideoSourceAuthorizationStatus.AUTHORIZED
    source.authorized_by_user = user
    source.authorized_at = timezone.now()
    source.authorization_reference = "test-source-approval-v1"
    source.save(
        update_fields=[
            "authorization_status",
            "authorized_by_user",
            "authorized_at",
            "authorization_reference",
            "updated_at",
        ]
    )
    return source


def make_event(source: VideoSource, external_id: str) -> DetectionEvent:
    return DetectionEvent.objects.create(
        video_source=source,
        external_event_id=external_id,
        service_principal_ref="AI_SERVICE",
        model_name="resqvision-test-detector",
        model_version="1.0.0",
        detected_at=timezone.now(),
        processing_outcome=DetectionEvent.ProcessingOutcome.OBSERVATION,
        auxiliary_metadata={"schema": 1},
    )


def candidate_from_event(source: VideoSource, user, external_id="candidate-event"):
    authorize_fixture_source(source, user)
    event = make_event(source, external_id)
    candidate = create_candidate(
        detection_event_id=event.pk,
        actor=MachineActor("AI_SERVICE"),
    )
    return event, candidate


def add_membership(user, organization: Organization) -> OrganizationMembership:
    group = Group.objects.get(name=organization.organization_kind)
    return OrganizationMembership.objects.create(
        user=user,
        organization=organization,
        role_group=group,
    )


def new_organization(*, code: str, kind: str) -> Organization:
    return Organization.objects.create(
        code=code,
        display_name=code.replace("-", " ").title(),
        organization_kind=kind,
    )


@pytest.mark.django_db
def test_ai_event_ingestion_authorization_idempotency_and_provenance(video_source, user):
    source = authorize_fixture_source(video_source, user)
    command = ai_event_command(source, external_id="event-idempotent")

    accepted = ingest_detection_event(command)
    replay = ingest_detection_event(command)

    assert accepted.pk == replay.pk
    assert accepted.payload_sha256
    assert DetectionEvent.objects.filter(video_source=source).count() == 1
    assert AuditEvent.objects.filter(action="DETECTION_EVENT_ACCEPTED").count() == 1
    assert AuditEvent.objects.filter(action="DETECTION_EVENT_REPLAYED").count() == 1

    conflicting = ai_event_command(source, external_id="event-idempotent", version="2.0.0")
    with pytest.raises(IdempotencyConflict):
        ingest_detection_event(conflicting)
    assert DetectionEvent.objects.filter(video_source=source).count() == 1


@pytest.mark.django_db
def test_ai_event_ingestion_denies_unapproved_source_and_records_denial(video_source):
    command = ai_event_command(video_source, external_id="blocked-event")

    with pytest.raises(AuthorizationDenied):
        ingest_detection_event(command)

    assert not DetectionEvent.objects.filter(external_event_id="blocked-event").exists()
    denial = AuditEvent.objects.get(action="DETECTION_EVENT_DENIED")
    assert denial.actor_service_ref == "AI_SERVICE"
    assert "auxiliary_metadata" not in denial.safe_context


@pytest.mark.django_db
def test_candidate_creation_association_review_and_default_deny(video_source, user):
    source = authorize_fixture_source(video_source, user)
    first = make_event(source, "candidate-first-event")
    candidate = create_candidate(detection_event_id=first.pk, actor=MachineActor("AI_SERVICE"))
    assert (
        create_candidate(detection_event_id=first.pk, actor=MachineActor("AI_SERVICE")).pk
        == candidate.pk
    )

    second = make_event(source, "candidate-second-event")
    link = associate_detection_event(
        candidate_id=candidate.pk,
        detection_event_id=second.pk,
        actor=HumanActor(user),
        policy=allow("candidate.associate"),
    )
    assert link.candidate_id == candidate.pk
    assert candidate.detection_links.count() == 2
    assert CandidateDetectionEvent.objects.filter(detection_event=second).count() == 1

    review_command = uuid4()
    started = begin_candidate_review(
        candidate_id=candidate.pk,
        actor=HumanActor(user),
        command_id=review_command,
        policy=allow("candidate.review"),
    )
    repeated = begin_candidate_review(
        candidate_id=candidate.pk,
        actor=HumanActor(user),
        command_id=review_command,
        policy=allow("candidate.review"),
    )
    assert started.value.status == CandidateStatus.UNDER_REVIEW
    assert repeated.replayed is True
    with pytest.raises(PolicyNotConfigured):
        verify_candidate(candidate_id=candidate.pk, actor=HumanActor(user), command_id=uuid4())
    with pytest.raises(AuthorizationDenied):
        reject_candidate(
            candidate_id=candidate.pk,
            actor=MachineActor("AI_SERVICE"),
            command_id=uuid4(),
            rationale="Machine actors cannot review candidates.",
            policy=allow("candidate.reject"),
        )


@pytest.mark.django_db
def test_candidate_rejection_requires_rationale_and_never_creates_incident(video_source, user):
    _, candidate = candidate_from_event(video_source, user, "reject-event")
    begin_candidate_review(
        candidate_id=candidate.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("candidate.review"),
    )
    with pytest.raises(InvalidStateTransition):
        reject_candidate(
            candidate_id=candidate.pk,
            actor=HumanActor(user),
            command_id=uuid4(),
            rationale="   ",
            policy=allow("candidate.reject"),
        )
    result = reject_candidate(
        candidate_id=candidate.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        rationale="Evidence did not meet the review threshold.",
        policy=allow("candidate.reject"),
    )
    candidate.refresh_from_db()
    assert result.value.pk == candidate.pk
    assert candidate.status == CandidateStatus.REJECTED
    assert not AccidentIncident.objects.filter(candidate=candidate).exists()


@pytest.mark.django_db
def test_candidate_verification_is_atomic_and_idempotent(video_source, user):
    _, candidate = candidate_from_event(video_source, user, "verify-event")
    begin_candidate_review(
        candidate_id=candidate.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("candidate.review"),
    )
    command_id = uuid4()
    policy = allow("candidate.verify")

    with patch(
        "apps.incidents.services.candidates.record_successful_action",
        side_effect=RuntimeError("forced audit write failure"),
    ):
        with pytest.raises(RuntimeError, match="forced audit write failure"):
            verify_candidate(
                candidate_id=candidate.pk,
                actor=HumanActor(user),
                command_id=command_id,
                policy=policy,
            )
    candidate.refresh_from_db()
    assert candidate.status == CandidateStatus.UNDER_REVIEW
    assert not CandidateReview.objects.filter(candidate=candidate).exists()
    assert not AccidentIncident.objects.filter(candidate=candidate).exists()

    created = verify_candidate(
        candidate_id=candidate.pk,
        actor=HumanActor(user),
        command_id=command_id,
        rationale="Reviewer confirmed the event.",
        policy=policy,
    )
    replay = verify_candidate(
        candidate_id=candidate.pk,
        actor=HumanActor(user),
        command_id=command_id,
        rationale=" Reviewer confirmed the event. ",
        policy=policy,
    )
    candidate.refresh_from_db()
    assert candidate.status == CandidateStatus.VERIFIED
    assert created.value.candidate_id == candidate.pk
    assert replay.replayed is True
    assert AccidentIncident.objects.filter(candidate=candidate).count() == 1
    assert (
        IncidentStatusHistory.objects.filter(incident=created.value, to_status="OPEN").count() == 1
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_candidate_verification_with_same_command_creates_one_incident(
    video_source, user
):
    _, candidate = candidate_from_event(video_source, user, "concurrent-review-event")
    begin_candidate_review(
        candidate_id=candidate.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("candidate.review"),
    )
    command_id = uuid4()
    gate = Barrier(2)
    user_id = user.pk
    candidate_id = candidate.pk

    def verify_from_thread():
        close_old_connections()
        try:
            reviewer = get_user_model().objects.get(pk=user_id)
            gate.wait(timeout=10)
            return verify_candidate(
                candidate_id=candidate_id,
                actor=HumanActor(reviewer),
                command_id=command_id,
                policy=allow("candidate.verify"),
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: verify_from_thread(), range(2)))

    assert sorted(result.replayed for result in results) == [False, True]
    assert AccidentIncident.objects.filter(candidate_id=candidate_id).count() == 1
    assert CandidateReview.objects.filter(candidate_id=candidate_id).count() == 1


@pytest.mark.django_db
def test_incident_resolution_and_closure_require_explicit_policy(incident, user):
    command_id = uuid4()
    with pytest.raises(PolicyNotConfigured):
        resolve_incident(
            incident_id=incident.pk,
            actor=HumanActor(user),
            command_id=command_id,
            reason="Resolved after review.",
        )
    resolved = resolve_incident(
        incident_id=incident.pk,
        actor=HumanActor(user),
        command_id=command_id,
        reason="Resolved after review.",
        policy=allow("incident.resolve"),
    )
    assert resolved.value.status == IncidentStatus.RESOLVED
    assert resolve_incident(
        incident_id=incident.pk,
        actor=HumanActor(user),
        command_id=command_id,
        reason="Resolved after review.",
        policy=allow("incident.resolve"),
    ).replayed
    closed = close_incident(
        incident_id=incident.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        reason="Closure review completed.",
        policy=allow("incident.close"),
    )
    assert closed.value.status == IncidentStatus.CLOSED
    with pytest.raises(InvalidStateTransition):
        resolve_incident(
            incident_id=incident.pk,
            actor=HumanActor(user),
            command_id=uuid4(),
            reason="Cannot resolve a closed incident.",
            policy=allow("incident.resolve"),
        )


@pytest.mark.django_db
def test_response_assignments_are_independent_and_reassignment_preserves_history(
    incident, user, police_organization, hospital_organization
):
    police_user = get_user_model().objects.create_user("police-domain@example.test", "test-pass")
    hospital_user = get_user_model().objects.create_user(
        "hospital-domain@example.test", "test-pass"
    )
    add_membership(police_user, police_organization)
    add_membership(hospital_user, hospital_organization)
    assignment_policy = allow("assignment.create")
    police = create_assignment(
        incident_id=incident.pk,
        target_organization_id=police_organization.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=assignment_policy,
    ).value
    hospital = create_assignment(
        incident_id=incident.pk,
        target_organization_id=hospital_organization.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=assignment_policy,
    ).value

    ack_command = uuid4()
    acknowledged = acknowledge_assignment(
        assignment_id=police.pk,
        actor=HumanActor(police_user),
        command_id=ack_command,
    )
    assert acknowledged.value.status == AssignmentStatus.ACKNOWLEDGED
    assert acknowledge_assignment(
        assignment_id=police.pk,
        actor=HumanActor(police_user),
        command_id=ack_command,
    ).replayed
    hospital.refresh_from_db()
    assert hospital.status == AssignmentStatus.PENDING

    acknowledge_assignment(
        assignment_id=hospital.pk,
        actor=HumanActor(hospital_user),
        command_id=uuid4(),
    )
    start_command = uuid4()
    started = start_response(
        assignment_id=hospital.pk,
        actor=HumanActor(hospital_user),
        command_id=start_command,
        details="Readiness confirmed.",
    )
    activity = Response.objects.get(command_id=start_command)
    assert started.value.status == AssignmentStatus.IN_PROGRESS
    assert activity.activity_kind == ResponseActivityKind.READINESS_UPDATE
    incident.refresh_from_db()
    assert incident.status == IncidentStatus.RESPONSE_ACTIVE
    with pytest.raises(IdempotencyConflict):
        start_response(
            assignment_id=hospital.pk,
            actor=HumanActor(hospital_user),
            command_id=start_command,
            details="Different response details.",
        )

    replacement_target = new_organization(code="north-police", kind=Organization.Kind.POLICE)
    reassignment_command = uuid4()
    replacement = reassign_assignment(
        assignment_id=police.pk,
        target_organization_id=replacement_target.pk,
        actor=HumanActor(user),
        command_id=reassignment_command,
        reason="Coverage moved to the northern district.",
        policy=allow("assignment.reassign"),
    )
    old_assignment = ResponseAssignment.objects.get(pk=police.pk)
    assert old_assignment.status == AssignmentStatus.CANCELLED
    assert replacement.value.replacement_for_id == police.pk
    assert ResponseAssignment.objects.filter(pk=police.pk).exists()
    assert AssignmentStatusHistory.objects.filter(command_id=reassignment_command).count() == 1
    replay = reassign_assignment(
        assignment_id=police.pk,
        target_organization_id=replacement_target.pk,
        actor=HumanActor(user),
        command_id=reassignment_command,
        reason="Coverage moved to the northern district.",
        policy=allow("assignment.reassign"),
    )
    assert replay.value.pk == replacement.value.pk
    assert replay.replayed


@pytest.mark.django_db
def test_assignment_creation_denies_unconfigured_policy_and_wrong_membership(
    incident, user, police_organization
):
    with pytest.raises(PolicyNotConfigured):
        create_assignment(
            incident_id=incident.pk,
            target_organization_id=police_organization.pk,
            actor=HumanActor(user),
            command_id=uuid4(),
        )
    assignment = create_assignment(
        incident_id=incident.pk,
        target_organization_id=police_organization.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("assignment.create"),
    ).value
    with pytest.raises(AuthorizationDenied):
        acknowledge_assignment(
            assignment_id=assignment.pk,
            actor=HumanActor(user),
            command_id=uuid4(),
        )
    assert assignment.status == AssignmentStatus.PENDING


@pytest.mark.django_db
def test_evidence_upload_validation_access_expiry_and_deletion(user):
    machine = MachineActor("AI_SERVICE")
    asset = create_evidence_asset(
        actor=machine,
        storage_provider="private-test-store",
        storage_namespace="resqvision-tests",
        object_key="evidence/private-object-001",
        retention_policy_ref="test-retention-v1",
    )
    with pytest.raises(BusinessRuleViolation):
        create_evidence_asset(
            actor=machine,
            storage_provider="private-test-store",
            storage_namespace="resqvision-tests",
            object_key="https://example.test/signed-object",
            retention_policy_ref="test-retention-v1",
        )
    session = create_upload_session(
        evidence_id=asset.pk,
        actor=machine,
        expires_at=timezone.now() + timedelta(minutes=10),
        policy=allow("evidence.upload.create"),
    )
    authorize_upload_session(
        session_id=session.pk,
        actor=machine,
        policy=allow("evidence.upload.authorize"),
    )

    class VerifiedStore:
        def verify_upload(self, _asset, _session):
            return StorageVerification(
                exists=True,
                size_bytes=4096,
                checksum_sha256="c" * 64,
                media_type="video/mp4",
                uploaded_at=timezone.now(),
            )

    quarantined = complete_upload(
        session_id=session.pk,
        actor=machine,
        verifier=VerifiedStore(),
        policy=allow("evidence.upload.complete"),
    )
    assert quarantined.status == EvidenceStatus.QUARANTINED
    with pytest.raises(PolicyNotConfigured):
        mark_evidence_available(evidence_id=asset.pk, actor=HumanActor(user))
    validate_evidence(
        evidence_id=asset.pk,
        actor=HumanActor(user),
        validation=EvidenceValidation("PASSED", timezone.now()),
        policy=allow("evidence.validate"),
    )
    available = mark_evidence_available(
        evidence_id=asset.pk,
        actor=HumanActor(user),
        policy=allow("evidence.publish"),
    )
    assert available.status == EvidenceStatus.AVAILABLE
    assert (
        record_evidence_access(
            evidence_id=asset.pk,
            actor=HumanActor(user),
            policy=allow("evidence.access"),
        ).pk
        == asset.pk
    )
    expired = expire_evidence(
        evidence_id=asset.pk,
        actor=HumanActor(user),
        policy=allow("evidence.expire"),
    )
    assert expired.status == EvidenceStatus.EXPIRED
    with pytest.raises(ResourceNotFound):
        record_evidence_access(
            evidence_id=asset.pk,
            actor=HumanActor(user),
            policy=allow("evidence.access"),
        )

    class DeletedStore:
        def confirm_absent(self, _asset):
            return True

    deleted = mark_evidence_deleted(
        evidence_id=asset.pk,
        actor=HumanActor(user),
        deletion_verifier=DeletedStore(),
        policy=allow("evidence.delete.confirm"),
    )
    assert deleted.status == EvidenceStatus.DELETED


@pytest.mark.django_db
def test_evidence_cannot_be_available_without_validated_metadata(user):
    asset = EvidenceAsset.objects.create(
        created_by_user=user,
        storage_provider="private-test-store",
        storage_namespace="resqvision-tests",
        object_key="evidence/unvalidated-object",
        retention_policy_ref="test-retention-v1",
        status=EvidenceStatus.QUARANTINED,
    )
    with pytest.raises(BusinessRuleViolation):
        mark_evidence_available(
            evidence_id=asset.pk,
            actor=HumanActor(user),
            policy=allow("evidence.publish"),
        )
    asset.refresh_from_db()
    assert asset.status == EvidenceStatus.QUARANTINED


@pytest.mark.django_db
def test_location_verification_correction_and_camera_separation(candidate, user, video_source):
    claim = create_location_claim(
        actor=MachineActor("AI_SERVICE"),
        claim_kind=LocationRecord.ClaimKind.ACCIDENT_LOCATION,
        source_method=LocationRecord.SourceMethod.INFERRED,
        subject_candidate_id=candidate.pk,
        latitude=Decimal("40.712800"),
        longitude=Decimal("-74.006000"),
        accuracy_m=Decimal("12.50"),
    )
    with pytest.raises(PolicyNotConfigured):
        verify_location_claim(location_id=claim.pk, actor=HumanActor(user))
    verified = verify_location_claim(
        location_id=claim.pk,
        actor=HumanActor(user),
        policy=allow("location.verify"),
    )
    corrected = correct_location_claim(
        location_id=claim.pk,
        actor=HumanActor(user),
        latitude=Decimal("40.713000"),
        longitude=Decimal("-74.005800"),
        accuracy_m=Decimal("10.00"),
        reason="Reviewer corrected the map pin.",
        policy=allow("location.correct"),
    )
    assert verified.verification_status == LocationRecord.VerificationStatus.VERIFIED
    assert corrected.verification_status == LocationRecord.VerificationStatus.CORRECTED
    history = LocationCorrectionHistory.objects.get(location_record=claim)
    assert history.previous_latitude == Decimal("40.712800")
    assert history.new_latitude == Decimal("40.713000")
    assert (
        get_current_location_claim(
            actor=HumanActor(user),
            subject_candidate_id=candidate.pk,
            policy=allow("location.read"),
        ).pk
        == claim.pk
    )
    with pytest.raises(BusinessRuleViolation):
        create_location_claim(
            actor=HumanActor(user),
            claim_kind=LocationRecord.ClaimKind.ACCIDENT_LOCATION,
            source_method=LocationRecord.SourceMethod.INFERRED,
            subject_video_source_id=video_source.pk,
            policy=allow("location.create"),
        )


@pytest.mark.django_db
def test_location_rejects_invalid_coordinates_and_missing_correction_reason(candidate, user):
    with pytest.raises(BusinessRuleViolation):
        create_location_claim(
            actor=MachineActor("AI_SERVICE"),
            claim_kind=LocationRecord.ClaimKind.ACCIDENT_LOCATION,
            source_method=LocationRecord.SourceMethod.INFERRED,
            subject_candidate_id=candidate.pk,
            latitude=Decimal("91.000000"),
            longitude=Decimal("0.000000"),
        )


@pytest.mark.django_db
def test_simulated_notification_retries_are_idempotent_and_do_not_change_assignment(
    incident, user, police_organization
):
    recipient = get_user_model().objects.create_user("notify-police@example.test", "test-pass")
    add_membership(recipient, police_organization)
    assignment = create_assignment(
        incident_id=incident.pk,
        target_organization_id=police_organization.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("assignment.create"),
    ).value
    create_command = uuid4()
    notification = create_notification(
        actor=HumanActor(user),
        recipient_user_id=recipient.pk,
        safe_message_code="ASSIGNMENT_PENDING",
        command_id=create_command,
        assignment_id=assignment.pk,
        policy=allow("notification.create"),
    )
    replay = create_notification(
        actor=HumanActor(user),
        recipient_user_id=recipient.pk,
        safe_message_code="ASSIGNMENT_PENDING",
        command_id=create_command,
        assignment_id=assignment.pk,
        policy=allow("notification.create"),
    )
    assert replay.value.pk == notification.value.pk
    assert replay.replayed

    mark_notification_pending(
        notification_id=notification.value.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("notification.pending"),
    )
    failed = record_delivery_failure(
        notification_id=notification.value.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        safe_failure_code="SIMULATED_UNAVAILABLE",
        policy=allow("notification.fail"),
    )
    assert failed.value.outcome == NotificationDeliveryAttempt.Outcome.FAILED
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.PENDING

    mark_notification_pending(
        notification_id=notification.value.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("notification.pending"),
    )
    delivery_command = uuid4()
    delivery = record_simulated_delivery(
        notification_id=notification.value.pk,
        actor=HumanActor(user),
        command_id=delivery_command,
        policy=allow("notification.deliver"),
    )
    assert delivery.value.outcome == NotificationDeliveryAttempt.Outcome.DELIVERED_SIMULATED
    assert record_simulated_delivery(
        notification_id=notification.value.pk,
        actor=HumanActor(user),
        command_id=delivery_command,
        policy=allow("notification.deliver"),
    ).replayed
    read = mark_notification_read(
        notification_id=notification.value.pk,
        actor=HumanActor(recipient),
        command_id=uuid4(),
    )
    assert read.value.status == Notification.Status.READ
    assignment.refresh_from_db()
    incident.refresh_from_db()
    assert assignment.status == AssignmentStatus.PENDING
    assert incident.status == IncidentStatus.OPEN
    assert not AuditEvent.objects.filter(
        resource_id=notification.value.pk,
        safe_context__token__isnull=False,
    ).exists()


@pytest.mark.django_db
def test_notification_read_is_scoped_to_recipient_and_audited(incident, user):
    recipient = get_user_model().objects.create_user("recipient@example.test", "test-pass")
    outsider = get_user_model().objects.create_user("outsider@example.test", "test-pass")
    notification = create_notification(
        actor=HumanActor(user),
        recipient_user_id=recipient.pk,
        safe_message_code="INCIDENT_CREATED",
        command_id=uuid4(),
        incident_id=incident.pk,
        policy=allow("notification.create"),
    ).value
    mark_notification_pending(
        notification_id=notification.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("notification.pending"),
    )
    record_simulated_delivery(
        notification_id=notification.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("notification.deliver"),
    )
    with pytest.raises(AuthorizationDenied):
        mark_notification_read(
            notification_id=notification.pk,
            actor=HumanActor(outsider),
            command_id=uuid4(),
        )
    assert AuditEvent.objects.filter(
        resource_id=notification.pk,
        action="DOMAIN_ACTION_DENIED",
    ).exists()
    incident.refresh_from_db()
    assert incident.status == IncidentStatus.OPEN


@pytest.mark.django_db
def test_membership_scope_and_source_authorization_use_explicit_policy(
    user, video_source, police_organization
):
    membership = add_membership(user, police_organization)
    assert (
        validate_organization_membership(
            actor=HumanActor(user),
            organization_id=police_organization.pk,
            expected_role="POLICE",
        ).pk
        == membership.pk
    )
    suspended = suspend_membership(
        membership_id=membership.pk,
        actor=HumanActor(user),
        command_id=uuid4(),
        policy=allow("membership.suspended"),
    )
    assert suspended.status == OrganizationMembership.Status.SUSPENDED
    with pytest.raises(AuthorizationDenied):
        validate_organization_membership(
            actor=HumanActor(user),
            organization_id=police_organization.pk,
            expected_role="POLICE",
        )

    with pytest.raises(PolicyNotConfigured):
        authorize_video_source(
            source_id=video_source.pk,
            actor=HumanActor(user),
            authorization_reference="approval-record-42",
        )
    authorized = authorize_video_source(
        source_id=video_source.pk,
        actor=HumanActor(user),
        authorization_reference="approval-record-42",
        policy=allow("source.authorize"),
    )
    assert authorized.authorization_status == VideoSourceAuthorizationStatus.AUTHORIZED
    assert authorized.authorization_reference == "approval-record-42"

    registered = register_video_source(
        actor=HumanActor(user),
        source_code="manual-demo-source",
        name="Manual demo source",
        source_type=VideoSource.SourceType.CONTROLLED_FILE,
        owner_external_ref="demo-owner-ref",
        processing_policy_ref="approved-test-processing",
        retention_policy_ref="test-retention-v1",
        policy=allow("source.register"),
    )
    assert registered.authorization_status == VideoSource.AuthorizationStatus.PENDING_REVIEW


@pytest.mark.django_db
def test_audit_service_rejects_unapproved_context_keys(user):
    with pytest.raises(BusinessRuleViolation):
        record_audit_event(
            actor=HumanActor(user),
            action="DOMAIN_ACTION_DENIED",
            resource_type=AuditEvent.ResourceType.INCIDENT,
            safe_context={"token": "must-never-be-logged"},
        )
