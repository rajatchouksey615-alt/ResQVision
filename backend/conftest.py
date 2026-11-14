"""Shared PostgreSQL-backed fixtures for domain model tests."""

import pytest

from apps.accounts.models import User
from apps.detection.models import DetectionEvent
from apps.incidents.models import AccidentCandidate, AccidentIncident
from apps.organizations.models import Organization
from apps.sources.models import VideoSource


@pytest.fixture
def user(db):
    return User.objects.create_user("reviewer@example.test", "local-test-password")


@pytest.fixture
def police_organization(db):
    return Organization.objects.create(
        code="central-police",
        display_name="Central Police",
        organization_kind=Organization.Kind.POLICE,
    )


@pytest.fixture
def hospital_organization(db):
    return Organization.objects.create(
        code="central-hospital",
        display_name="Central Hospital",
        organization_kind=Organization.Kind.HOSPITAL,
    )


@pytest.fixture
def video_source(db):
    return VideoSource.objects.create(
        source_code="demo-camera-001",
        name="Demo Camera",
        source_type=VideoSource.SourceType.CAMERA_STREAM,
        owner_external_ref="demo-owner",
        processing_policy_ref="approved-demo-policy-v1",
        retention_policy_ref="demo-retention-policy-v1",
    )


@pytest.fixture
def detection_event(db, video_source):
    return DetectionEvent.objects.create(
        video_source=video_source,
        external_event_id="demo-event-001",
        service_principal_ref="AI_SERVICE",
        model_name="resqvision-demo-detector",
        model_version="1.0.0",
        detected_at="2026-11-14T12:00:00Z",
        processing_outcome=DetectionEvent.ProcessingOutcome.OBSERVATION,
        confidence="0.8500",
        payload_sha256="a" * 64,
        auxiliary_metadata={"schema": 1},
    )


@pytest.fixture
def candidate(db):
    return AccidentCandidate.objects.create()


@pytest.fixture
def incident(db, candidate):
    return AccidentIncident.objects.create(candidate=candidate)
