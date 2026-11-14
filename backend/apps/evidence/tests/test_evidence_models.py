from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.evidence.models import (
    EvidenceAsset,
    EvidenceAssociation,
    EvidenceUploadSession,
)


def asset_values(**overrides):
    values = {
        "created_by_service_ref": "AI_SERVICE",
        "storage_provider": "private-demo-store",
        "storage_namespace": "resqvision-private",
        "object_key": "evidence/opaque-object-001",
        "retention_policy_ref": "demo-retention-policy-v1",
    }
    values.update(overrides)
    return values


@pytest.mark.django_db
def test_evidence_keeps_private_storage_reference_and_metadata(evidence_asset):
    assert evidence_asset.object_key == "evidence/opaque-object-001"
    assert evidence_asset.status == EvidenceAsset.Status.PENDING_UPLOAD


@pytest.fixture
def evidence_asset(db):
    return EvidenceAsset.objects.create(**asset_values())


@pytest.mark.django_db
def test_available_evidence_requires_upload_and_validation_metadata():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EvidenceAsset.objects.create(**asset_values(status=EvidenceAsset.Status.AVAILABLE))


@pytest.mark.django_db
def test_validated_evidence_can_become_available():
    asset = EvidenceAsset.objects.create(
        **asset_values(
            object_key="evidence/opaque-object-available",
            status=EvidenceAsset.Status.AVAILABLE,
            scan_status=EvidenceAsset.ScanStatus.PASSED,
            validation_completed_at=timezone.now(),
            uploaded_at=timezone.now(),
            size_bytes=2048,
            checksum_sha256="b" * 64,
            media_type="video/mp4",
        )
    )

    assert asset.status == EvidenceAsset.Status.AVAILABLE


@pytest.mark.django_db
def test_storage_object_reference_is_unique():
    EvidenceAsset.objects.create(**asset_values())

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EvidenceAsset.objects.create(**asset_values())


@pytest.mark.django_db
def test_evidence_association_requires_exactly_one_target(evidence_asset, candidate, incident):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EvidenceAssociation.objects.create(
                evidence_asset=evidence_asset,
                candidate=candidate,
                incident=incident,
            )


@pytest.mark.django_db
def test_evidence_can_be_linked_once_to_candidate_and_resulting_incident(
    evidence_asset, candidate, incident
):
    EvidenceAssociation.objects.create(evidence_asset=evidence_asset, candidate=candidate)
    EvidenceAssociation.objects.create(evidence_asset=evidence_asset, incident=incident)

    assert evidence_asset.associations.count() == 2


@pytest.mark.django_db
def test_only_one_active_upload_session_exists_per_asset(evidence_asset):
    expires = timezone.now() + timedelta(minutes=10)
    EvidenceUploadSession.objects.create(
        evidence_asset=evidence_asset,
        service_ref="AI_SERVICE",
        expires_at=expires,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EvidenceUploadSession.objects.create(
                evidence_asset=evidence_asset,
                service_ref="AI_SERVICE",
                expires_at=expires,
            )


@pytest.mark.django_db
def test_failed_upload_session_requires_safe_failure_code(evidence_asset):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EvidenceUploadSession.objects.create(
                evidence_asset=evidence_asset,
                service_ref="AI_SERVICE",
                status=EvidenceUploadSession.Status.FAILED,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
