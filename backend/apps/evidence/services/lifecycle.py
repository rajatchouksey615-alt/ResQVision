"""Evidence metadata and upload lifecycle coordination without a storage SDK."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_denied_action, record_successful_action
from apps.detection.models import DetectionEvent
from apps.evidence.models import (
    EvidenceAsset,
    EvidenceScanStatus,
    EvidenceStatus,
    EvidenceUploadSession,
    UploadSessionStatus,
)
from common.domain.actors import Actor, HumanActor, MachineActor
from common.domain.authorization import require_ai_service, require_human, require_known_actor
from common.domain.exceptions import (
    AuthorizationDenied,
    BusinessRuleViolation,
    InvalidStateTransition,
    PolicyNotConfigured,
    ResourceConflict,
    ResourceNotFound,
)
from common.domain.policies import AuthorizationPolicy, require_authorized


@dataclass(frozen=True, slots=True)
class StorageVerification:
    exists: bool
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    media_type: str | None = None
    uploaded_at: datetime | None = None


class StorageVerifier(Protocol):
    def verify_upload(
        self, asset: EvidenceAsset, session: EvidenceUploadSession
    ) -> StorageVerification:
        """Inspect one opaque object reference and return trusted metadata."""


class StorageDeletionVerifier(Protocol):
    def confirm_absent(self, asset: EvidenceAsset) -> bool:
        """Return true only after the object is confirmed absent."""


@dataclass(frozen=True, slots=True)
class EvidenceValidation:
    scan_status: str
    validation_completed_at: datetime


def _audit_denied(actor: Actor, evidence_id: UUID | None, operation: str) -> None:
    record_denied_action(
        actor=actor,
        action="DOMAIN_ACTION_DENIED",
        resource_type="EVIDENCE",
        resource_id=evidence_id,
        safe_context={"reason_code": operation},
    )


def _validate_storage_reference(
    *, storage_provider: str, storage_namespace: str, object_key: str
) -> None:
    if not all(
        value and value.strip() for value in (storage_provider, storage_namespace, object_key)
    ):
        raise BusinessRuleViolation("Private storage references must be non-empty.")
    if any(token in object_key for token in ("://", "?", "#")) or object_key.startswith("/"):
        raise BusinessRuleViolation("Evidence must use an opaque private object key, not a URL.")


def _creator_fields(actor: Actor) -> dict[str, object]:
    if isinstance(actor, HumanActor):
        return {"created_by_user": require_human(actor), "created_by_service_ref": None}
    machine = require_ai_service(actor)
    return {"created_by_user": None, "created_by_service_ref": machine.service_ref}


def create_evidence_asset(
    *,
    actor: Actor,
    storage_provider: str,
    storage_namespace: str,
    object_key: str,
    retention_policy_ref: str,
    source_detection_event_id: UUID | None = None,
    original_filename: str | None = None,
    policy: AuthorizationPolicy | None = None,
) -> EvidenceAsset:
    try:
        if isinstance(actor, HumanActor):
            require_human(actor)
        else:
            require_ai_service(actor)
        _validate_storage_reference(
            storage_provider=storage_provider,
            storage_namespace=storage_namespace,
            object_key=object_key,
        )
        event = None
        if source_detection_event_id is not None:
            event = DetectionEvent.objects.filter(pk=source_detection_event_id).first()
            if event is None:
                raise ResourceNotFound("Detection event was not found.")
        asset = EvidenceAsset(
            **_creator_fields(actor),
            source_detection_event=event,
            storage_provider=storage_provider,
            storage_namespace=storage_namespace,
            object_key=object_key,
            original_filename=original_filename,
            retention_policy_ref=retention_policy_ref,
            status=EvidenceStatus.PENDING_UPLOAD,
        )
        if isinstance(actor, HumanActor):
            require_authorized(policy, "evidence.create", actor, asset)
        asset.full_clean()
        asset.save()
        record_successful_action(
            actor=actor,
            action="EVIDENCE_CREATED",
            resource_type="EVIDENCE",
            resource_id=asset.pk,
        )
        return asset
    except AuthorizationDenied, PolicyNotConfigured:
        _audit_denied(actor, None, "evidence.create")
        raise
    except IntegrityError as exc:
        raise ResourceConflict("The private storage reference is already registered.") from exc
    except DjangoValidationError as exc:
        raise BusinessRuleViolation("Evidence metadata did not pass validation.") from exc


def create_upload_session(
    *,
    evidence_id: UUID,
    actor: Actor,
    expires_at: datetime,
    policy: AuthorizationPolicy | None = None,
) -> EvidenceUploadSession:
    try:
        if isinstance(actor, HumanActor):
            require_human(actor)
            service_ref = "BACKEND"
        else:
            service_ref = require_ai_service(actor).service_ref
        if (
            expires_at.tzinfo is None
            or expires_at.utcoffset() is None
            or expires_at <= timezone.now()
        ):
            raise BusinessRuleViolation(
                "Upload session expiry must be a future timezone-aware time."
            )
        with transaction.atomic():
            asset = EvidenceAsset.objects.select_for_update().filter(pk=evidence_id).first()
            if asset is None:
                raise ResourceNotFound("Evidence asset was not found.")
            require_authorized(policy, "evidence.upload.create", actor, asset)
            if asset.status not in {EvidenceStatus.PENDING_UPLOAD, EvidenceStatus.FAILED}:
                raise InvalidStateTransition("Evidence asset cannot start another upload now.")
            session = EvidenceUploadSession.objects.create(
                evidence_asset=asset,
                service_ref=service_ref,
                expires_at=expires_at,
                status=UploadSessionStatus.CREATED,
            )
            asset.status = EvidenceStatus.UPLOADING
            asset.save(update_fields=["status"])
            record_successful_action(
                actor=actor,
                action="EVIDENCE_UPLOAD_SESSION_CREATED",
                resource_type="EVIDENCE",
                resource_id=asset.pk,
                safe_context={"evidence_id": asset.pk},
            )
            return session
    except AuthorizationDenied, PolicyNotConfigured:
        _audit_denied(actor, evidence_id, "evidence.upload.create")
        raise
    except IntegrityError as exc:
        raise ResourceConflict(
            "An active upload session already exists for this evidence."
        ) from exc


def authorize_upload_session(
    *, session_id: UUID, actor: Actor, policy: AuthorizationPolicy | None = None
) -> EvidenceUploadSession:
    try:
        with transaction.atomic():
            session = (
                EvidenceUploadSession.objects.select_for_update()
                .select_related("evidence_asset")
                .filter(pk=session_id)
                .first()
            )
            if session is None:
                raise ResourceNotFound("Upload session was not found.")
            require_authorized(policy, "evidence.upload.authorize", actor, session)
            if isinstance(actor, HumanActor):
                require_human(actor)
            else:
                machine = require_ai_service(actor)
                if session.service_ref != machine.service_ref:
                    raise AuthorizationDenied("The machine actor does not own this upload session.")
            if (
                session.status != UploadSessionStatus.CREATED
                or session.expires_at <= timezone.now()
            ):
                raise InvalidStateTransition(
                    "Upload session cannot be authorized in its current state."
                )
            session.status = UploadSessionStatus.AUTHORIZED
            session.authorized_at = timezone.now()
            session.save(update_fields=["status", "authorized_at"])
            record_successful_action(
                actor=actor,
                action="EVIDENCE_UPLOAD_AUTHORIZED",
                resource_type="EVIDENCE",
                resource_id=session.evidence_asset_id,
            )
            return session
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition:
        _audit_denied(actor, session_id, "evidence.upload.authorize")
        raise


def complete_upload(
    *,
    session_id: UUID,
    actor: Actor,
    verifier: StorageVerifier,
    policy: AuthorizationPolicy | None = None,
) -> EvidenceAsset:
    try:
        if isinstance(actor, HumanActor):
            require_human(actor)
        else:
            machine = require_ai_service(actor)
        session = (
            EvidenceUploadSession.objects.select_related("evidence_asset")
            .filter(pk=session_id)
            .first()
        )
        if session is None:
            raise ResourceNotFound("Upload session was not found.")
        require_authorized(policy, "evidence.upload.complete", actor, session)
        if isinstance(actor, MachineActor) and session.service_ref != machine.service_ref:
            raise AuthorizationDenied("The machine actor does not own this upload session.")
        if session.status == UploadSessionStatus.COMPLETED:
            return session.evidence_asset
        if session.status not in {UploadSessionStatus.AUTHORIZED, UploadSessionStatus.UPLOADING}:
            raise InvalidStateTransition("Upload session is not authorized for completion.")
        if session.expires_at <= timezone.now():
            raise InvalidStateTransition("Upload session has expired.")
        # Storage I/O happens before opening the write transaction.
        verification = verifier.verify_upload(session.evidence_asset, session)
        with transaction.atomic():
            session = (
                EvidenceUploadSession.objects.select_for_update()
                .select_related("evidence_asset")
                .filter(pk=session_id)
                .first()
            )
            if session is None:
                raise ResourceNotFound("Upload session was not found.")
            require_authorized(policy, "evidence.upload.complete", actor, session)
            asset = EvidenceAsset.objects.select_for_update().get(pk=session.evidence_asset_id)
            if session.status == UploadSessionStatus.COMPLETED:
                return asset
            if session.status not in {
                UploadSessionStatus.AUTHORIZED,
                UploadSessionStatus.UPLOADING,
            }:
                raise InvalidStateTransition("Upload session is not authorized for completion.")
            if session.expires_at <= timezone.now():
                raise InvalidStateTransition("Upload session has expired.")
            if not verification.exists:
                session.status = UploadSessionStatus.FAILED
                session.failure_code = "OBJECT_NOT_FOUND"
                session.save(update_fields=["status", "failure_code"])
                asset.status = EvidenceStatus.FAILED
                asset.save(update_fields=["status"])
                record_successful_action(
                    actor=actor,
                    action="EVIDENCE_UPLOAD_FAILED",
                    resource_type="EVIDENCE",
                    resource_id=asset.pk,
                    safe_context={"failure_code": "OBJECT_NOT_FOUND"},
                )
                return asset
            if (
                verification.size_bytes is None
                or verification.size_bytes <= 0
                or verification.media_type is None
                or not verification.media_type.strip()
                or verification.checksum_sha256 is None
                or re.fullmatch(r"[0-9a-f]{64}", verification.checksum_sha256) is None
                or verification.uploaded_at is None
                or verification.uploaded_at.tzinfo is None
            ):
                raise BusinessRuleViolation("Storage verification returned incomplete metadata.")
            asset.size_bytes = verification.size_bytes
            asset.media_type = verification.media_type
            asset.checksum_sha256 = verification.checksum_sha256
            asset.uploaded_at = verification.uploaded_at
            asset.status = EvidenceStatus.QUARANTINED
            asset.save(
                update_fields=[
                    "size_bytes",
                    "media_type",
                    "checksum_sha256",
                    "uploaded_at",
                    "status",
                ]
            )
            session.status = UploadSessionStatus.COMPLETED
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at"])
            record_successful_action(
                actor=actor,
                action="EVIDENCE_UPLOAD_COMPLETED",
                resource_type="EVIDENCE",
                resource_id=asset.pk,
            )
            return asset
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, BusinessRuleViolation:
        _audit_denied(actor, session_id, "evidence.upload.complete")
        raise


def fail_upload(
    *, session_id: UUID, actor: Actor, safe_failure_code: str, policy=None
) -> EvidenceUploadSession:
    try:
        require_known_actor(actor)
        if not safe_failure_code or not safe_failure_code.strip():
            raise BusinessRuleViolation("A safe failure code is required.")
        with transaction.atomic():
            session = (
                EvidenceUploadSession.objects.select_for_update()
                .select_related("evidence_asset")
                .filter(pk=session_id)
                .first()
            )
            if session is None:
                raise ResourceNotFound("Upload session was not found.")
            require_authorized(policy, "evidence.upload.fail", actor, session)
            normalized_code = safe_failure_code.strip()[:64]
            if session.status == UploadSessionStatus.FAILED:
                if session.failure_code == normalized_code:
                    return session
                raise ResourceConflict("Upload failure was already recorded with another code.")
            if session.status in {UploadSessionStatus.COMPLETED, UploadSessionStatus.REVOKED}:
                raise InvalidStateTransition("Upload session cannot fail from this state.")
            session.status = UploadSessionStatus.FAILED
            session.failure_code = normalized_code
            session.save(update_fields=["status", "failure_code"])
            session.evidence_asset.status = EvidenceStatus.FAILED
            session.evidence_asset.save(update_fields=["status"])
            record_successful_action(
                actor=actor,
                action="EVIDENCE_UPLOAD_FAILED",
                resource_type="EVIDENCE",
                resource_id=session.evidence_asset_id,
                safe_context={"failure_code": session.failure_code},
            )
            return session
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, ResourceConflict:
        _audit_denied(actor, session_id, "evidence.upload.fail")
        raise


def validate_evidence(
    *, evidence_id: UUID, actor: Actor, validation: EvidenceValidation, policy=None
) -> EvidenceAsset:
    try:
        require_human(actor)
        if validation.scan_status not in EvidenceScanStatus.values:
            raise BusinessRuleViolation("Unsupported evidence scan status.")
        if (
            validation.validation_completed_at.tzinfo is None
            or validation.validation_completed_at.utcoffset() is None
        ):
            raise BusinessRuleViolation("Evidence validation time must include a timezone.")
        with transaction.atomic():
            asset = EvidenceAsset.objects.select_for_update().filter(pk=evidence_id).first()
            if asset is None:
                raise ResourceNotFound("Evidence asset was not found.")
            require_authorized(policy, "evidence.validate", actor, asset)
            if asset.status not in {EvidenceStatus.QUARANTINED, EvidenceStatus.FAILED}:
                raise InvalidStateTransition(
                    "Only quarantined or failed evidence can be validated."
                )
            asset.scan_status = validation.scan_status
            asset.validation_completed_at = validation.validation_completed_at
            asset.status = EvidenceStatus.QUARANTINED
            asset.save(update_fields=["scan_status", "validation_completed_at", "status"])
            record_successful_action(
                actor=actor,
                action="EVIDENCE_VALIDATED",
                resource_type="EVIDENCE",
                resource_id=asset.pk,
            )
            return asset
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, BusinessRuleViolation:
        _audit_denied(actor, evidence_id, "evidence.validate")
        raise


def mark_evidence_available(
    *, evidence_id: UUID, actor: Actor, policy: AuthorizationPolicy | None = None
) -> EvidenceAsset:
    try:
        require_human(actor)
        with transaction.atomic():
            asset = EvidenceAsset.objects.select_for_update().filter(pk=evidence_id).first()
            if asset is None:
                raise ResourceNotFound("Evidence asset was not found.")
            require_authorized(policy, "evidence.publish", actor, asset)
            if asset.status != EvidenceStatus.QUARANTINED:
                raise InvalidStateTransition("Only quarantined evidence can become available.")
            if (
                asset.scan_status
                not in {EvidenceScanStatus.NOT_REQUIRED, EvidenceScanStatus.PASSED}
                or asset.validation_completed_at is None
                or asset.uploaded_at is None
                or asset.size_bytes is None
                or not asset.media_type
                or not asset.checksum_sha256
            ):
                raise BusinessRuleViolation(
                    "Evidence does not have all required validation metadata."
                )
            asset.status = EvidenceStatus.AVAILABLE
            asset.save(update_fields=["status"])
            record_successful_action(
                actor=actor,
                action="EVIDENCE_AVAILABLE",
                resource_type="EVIDENCE",
                resource_id=asset.pk,
                safe_context={"evidence_id": asset.pk},
            )
            return asset
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, BusinessRuleViolation:
        _audit_denied(actor, evidence_id, "evidence.publish")
        raise


def record_evidence_access(
    *, evidence_id: UUID, actor: Actor, policy: AuthorizationPolicy | None = None
) -> EvidenceAsset:
    try:
        if isinstance(actor, HumanActor):
            require_human(actor)
        else:
            require_ai_service(actor)
        asset = EvidenceAsset.objects.filter(pk=evidence_id).first()
        if asset is None or asset.status != EvidenceStatus.AVAILABLE:
            raise ResourceNotFound("Evidence asset was not found.")
        require_authorized(policy, "evidence.access", actor, asset)
        record_successful_action(
            actor=actor,
            action="EVIDENCE_ACCESS_GRANTED",
            resource_type="EVIDENCE",
            resource_id=asset.pk,
        )
        return asset
    except AuthorizationDenied, PolicyNotConfigured, ResourceNotFound:
        record_denied_action(
            actor=actor,
            action="EVIDENCE_ACCESS_DENIED",
            resource_type="EVIDENCE",
            resource_id=evidence_id,
        )
        raise


def expire_evidence(
    *, evidence_id: UUID, actor: Actor, policy: AuthorizationPolicy | None = None
) -> EvidenceAsset:
    try:
        require_human(actor)
        with transaction.atomic():
            asset = EvidenceAsset.objects.select_for_update().filter(pk=evidence_id).first()
            if asset is None:
                raise ResourceNotFound("Evidence asset was not found.")
            require_authorized(policy, "evidence.expire", actor, asset)
            if asset.status in {EvidenceStatus.DELETED, EvidenceStatus.EXPIRED}:
                return asset
            asset.status = EvidenceStatus.EXPIRED
            asset.expired_at = timezone.now()
            asset.save(update_fields=["status", "expired_at"])
            record_successful_action(
                actor=actor,
                action="EVIDENCE_EXPIRED",
                resource_type="EVIDENCE",
                resource_id=asset.pk,
                safe_context={"evidence_id": asset.pk},
            )
            return asset
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition:
        _audit_denied(actor, evidence_id, "evidence.expire")
        raise


def mark_evidence_deleted(
    *,
    evidence_id: UUID,
    actor: Actor,
    deletion_verifier: StorageDeletionVerifier,
    policy: AuthorizationPolicy | None = None,
) -> EvidenceAsset:
    try:
        require_human(actor)
        asset = EvidenceAsset.objects.filter(pk=evidence_id).first()
        if asset is None:
            raise ResourceNotFound("Evidence asset was not found.")
        require_authorized(policy, "evidence.delete.confirm", actor, asset)
        if asset.status == EvidenceStatus.DELETED:
            return asset
        if asset.status != EvidenceStatus.EXPIRED:
            raise InvalidStateTransition("Evidence must be expired before deletion is confirmed.")
        # External storage confirmation stays outside the database transaction.
        if not deletion_verifier.confirm_absent(asset):
            raise InvalidStateTransition("Storage has not confirmed that the object is absent.")
        with transaction.atomic():
            asset = EvidenceAsset.objects.select_for_update().get(pk=evidence_id)
            require_authorized(policy, "evidence.delete.confirm", actor, asset)
            if asset.status == EvidenceStatus.DELETED:
                return asset
            if asset.status != EvidenceStatus.EXPIRED:
                raise InvalidStateTransition(
                    "Evidence must be expired before deletion is confirmed."
                )
            asset.status = EvidenceStatus.DELETED
            asset.deleted_at = timezone.now()
            asset.save(update_fields=["status", "deleted_at"])
            record_successful_action(
                actor=actor,
                action="EVIDENCE_DELETED",
                resource_type="EVIDENCE",
                resource_id=asset.pk,
                safe_context={"evidence_id": asset.pk},
            )
            return asset
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition:
        _audit_denied(actor, evidence_id, "evidence.delete.confirm")
        raise
