import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.sources.models import VideoSource


def source_values(**overrides):
    values = {
        "source_code": "camera-001",
        "name": "Main Street",
        "source_type": VideoSource.SourceType.CAMERA_STREAM,
        "owner_external_ref": "source-owner-1",
        "processing_policy_ref": "approved-demo-policy-v1",
        "retention_policy_ref": "demo-retention-policy-v1",
    }
    values.update(overrides)
    return values


@pytest.mark.django_db
def test_video_source_separates_authorization_from_availability():
    source = VideoSource.objects.create(**source_values())

    assert source.authorization_status == VideoSource.AuthorizationStatus.PENDING_REVIEW
    assert source.availability_status == VideoSource.AvailabilityStatus.UNKNOWN


@pytest.mark.django_db
def test_authorized_source_requires_human_approver_and_timestamp():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideoSource.objects.create(
                **source_values(authorization_status=VideoSource.AuthorizationStatus.AUTHORIZED)
            )


@pytest.mark.django_db
def test_authorized_source_can_reference_an_approver():
    user = User.objects.create_user("approver@example.com", "local-test-password")
    source = VideoSource.objects.create(
        **source_values(
            authorization_status=VideoSource.AuthorizationStatus.AUTHORIZED,
            authorized_by_user=user,
            authorized_at=timezone.now(),
        )
    )

    assert source.authorized_by_user == user


@pytest.mark.django_db
def test_video_source_requires_an_owner_reference():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideoSource.objects.create(
                **source_values(owner_external_ref=None, owner_organization=None)
            )


@pytest.mark.django_db
def test_video_source_can_use_an_organization_as_owner():
    organization = Organization.objects.create(
        code="source-owner",
        display_name="Source Owner",
        organization_kind=Organization.Kind.SOURCE_OWNER,
    )
    source = VideoSource.objects.create(
        **source_values(owner_external_ref=None, owner_organization=organization)
    )

    assert source.owner_organization == organization
