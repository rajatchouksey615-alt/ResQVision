"""Police organization resolution during transactional candidate creation."""

import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.detection.models import DetectionEvent
from apps.incidents.models import AccidentCandidate, CandidateDetectionEvent
from apps.incidents.services import create_candidate
from apps.organizations.models import Organization, OrganizationKind
from apps.sources.models import (
    VideoSource,
    VideoSourceAuthorizationStatus,
    VideoSourceAvailabilityStatus,
)
from common.domain.actors import MachineActor
from common.domain.exceptions import AuthorizationDenied


class AllowCandidateCreation:
    def authorize(self, operation, actor, resource=None):
        del actor, resource
        return operation == "candidate.create"


def prepare_source(source, user, *, police_organization=None, owner_organization=None):
    source.authorization_status = VideoSourceAuthorizationStatus.AUTHORIZED
    source.availability_status = VideoSourceAvailabilityStatus.AVAILABLE
    source.authorized_by_user = user
    source.authorized_at = timezone.now()
    source.owner_organization = owner_organization
    source.designated_police_organization = police_organization
    source.save(
        update_fields=[
            "authorization_status",
            "availability_status",
            "authorized_by_user",
            "authorized_at",
            "owner_organization",
            "designated_police_organization",
            "updated_at",
        ]
    )
    return source


def make_event(source, event_id):
    return DetectionEvent.objects.create(
        video_source=source,
        external_event_id=event_id,
        service_principal_ref="AI_SERVICE",
        model_name="routing-test-detector",
        model_version="1.0",
        detected_at=timezone.now(),
        processing_outcome=DetectionEvent.ProcessingOutcome.OBSERVATION,
    )


def create_from(event):
    return create_candidate(
        detection_event_id=event.pk,
        actor=MachineActor("AI_SERVICE"),
        policy=AllowCandidateCreation(),
    )


@pytest.mark.django_db
def test_candidate_uses_backend_designation_and_audits_persistent_binding(
    video_source, user, police_organization
):
    # Source ownership is independent from Police jurisdiction.
    source = prepare_source(
        video_source,
        user,
        police_organization=police_organization,
        owner_organization=police_organization,
    )
    event = make_event(source, "routed-event")

    candidate = create_from(event)

    assert candidate.police_organization_id == police_organization.pk
    assert CandidateDetectionEvent.objects.get(detection_event=event).candidate_id == candidate.pk
    audit = AuditEvent.objects.get(action="CANDIDATE_CREATED", resource_id=candidate.pk)
    assert audit.safe_context == {
        "event_id": str(event.pk),
        "source_id": str(source.pk),
        "organization_id": str(police_organization.pk),
    }


@pytest.mark.django_db
def test_missing_police_route_fails_closed_without_owner_fallback(
    video_source, user, police_organization
):
    source = prepare_source(
        video_source,
        user,
        owner_organization=police_organization,
    )
    event = make_event(source, "missing-route-event")

    with pytest.raises(AuthorizationDenied, match="no designated Police organization"):
        create_from(event)

    assert not AccidentCandidate.objects.exists()
    assert not CandidateDetectionEvent.objects.filter(detection_event=event).exists()
    assert AuditEvent.objects.filter(
        action="DOMAIN_ACTION_DENIED", outcome=AuditEvent.Outcome.DENIED
    ).exists()


@pytest.mark.django_db
def test_inactive_police_route_fails_closed(video_source, user, police_organization):
    police_organization.is_active = False
    police_organization.save(update_fields=["is_active", "updated_at"])
    source = prepare_source(video_source, user, police_organization=police_organization)
    event = make_event(source, "inactive-route-event")

    with pytest.raises(AuthorizationDenied, match="active Police organization"):
        create_from(event)

    assert not AccidentCandidate.objects.exists()


@pytest.mark.django_db
def test_non_police_route_fails_closed(video_source, user, hospital_organization):
    source = prepare_source(video_source, user, police_organization=hospital_organization)
    event = make_event(source, "wrong-organization-kind-event")

    with pytest.raises(AuthorizationDenied, match="active Police organization"):
        create_from(event)

    assert not AccidentCandidate.objects.exists()


@pytest.mark.django_db
def test_route_change_does_not_rewrite_existing_candidate_binding(
    video_source, user, police_organization
):
    next_police_organization = Organization.objects.create(
        code="north-police",
        display_name="North Police",
        organization_kind=OrganizationKind.POLICE,
    )
    source = prepare_source(video_source, user, police_organization=police_organization)
    first_event = make_event(source, "route-before-change")
    original_candidate = create_from(first_event)

    source.designated_police_organization = next_police_organization
    source.save(update_fields=["designated_police_organization", "updated_at"])
    replay = create_from(first_event)
    second_event = make_event(source, "route-after-change")
    next_candidate = create_from(second_event)

    original_candidate.refresh_from_db()
    assert replay.pk == original_candidate.pk
    assert original_candidate.police_organization_id == police_organization.pk
    assert next_candidate.police_organization_id == next_police_organization.pk
    assert AccidentCandidate.objects.count() == 2


@pytest.mark.django_db
def test_legacy_candidate_remains_unassigned_when_new_routed_candidate_is_created(
    video_source, user, police_organization
):
    legacy_candidate = AccidentCandidate.objects.create()
    original_updated_at = legacy_candidate.updated_at
    source = prepare_source(video_source, user, police_organization=police_organization)

    create_from(make_event(source, "new-candidate-after-migration"))

    legacy_candidate.refresh_from_db()
    assert legacy_candidate.police_organization_id is None
    assert legacy_candidate.updated_at == original_updated_at


@pytest.mark.django_db
def test_source_routing_is_single_valued_so_conflicting_active_routes_are_unrepresentable(
    video_source, police_organization
):
    field = VideoSource._meta.get_field("designated_police_organization")

    assert field.many_to_one
    assert field.remote_field.model is Organization
    assert field.null
    assert not field.one_to_many

    other_police_organization = Organization.objects.create(
        code="south-police",
        display_name="South Police",
        organization_kind=OrganizationKind.POLICE,
    )
    video_source.designated_police_organization = police_organization
    video_source.save(update_fields=["designated_police_organization", "updated_at"])
    video_source.designated_police_organization = other_police_organization
    video_source.save(update_fields=["designated_police_organization", "updated_at"])
    video_source.refresh_from_db()

    # There is one current foreign-key value per source, never multiple active route rows.
    assert video_source.designated_police_organization_id == other_police_organization.pk
