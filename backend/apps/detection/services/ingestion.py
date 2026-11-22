"""Idempotent ingestion for authenticated AI_SERVICE observations."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction

from apps.audit.services import record_denied_action, record_successful_action
from apps.detection.models import DetectionEvent, EventProcessingOutcome
from apps.sources.models import VideoSource
from apps.sources.services.registry import validate_source_for_ingestion
from common.domain.actors import Actor, MachineActor
from common.domain.authorization import require_ai_service, require_known_actor
from common.domain.exceptions import (
    AuthorizationDenied,
    BusinessRuleViolation,
    IdempotencyConflict,
    PolicyNotConfigured,
    ResourceNotFound,
)
from common.domain.policies import AuthorizationPolicy, require_authorized

_FORBIDDEN_EVENT_METADATA_KEYS = {
    "candidate_id",
    "candidate_status",
    "decision",
    "incident_id",
    "incident_status",
    "police_org_id",
    "police_organization_id",
    "review_decision",
    "reviewer",
    "reviewer_id",
    "verification",
    "verification_status",
    "verified",
}


@dataclass(frozen=True, slots=True)
class DetectionEventCommand:
    video_source_id: UUID
    external_event_id: str
    model_name: str
    model_version: str
    detected_at: datetime
    processing_outcome: str
    actor: MachineActor
    confidence: Decimal | None = None
    payload_sha256: str | None = None
    metadata_schema_version: int = 1
    auxiliary_metadata: dict[str, Any] | None = None


def _normalized_payload(command: DetectionEventCommand) -> dict[str, object]:
    return {
        "video_source_id": str(command.video_source_id),
        "external_event_id": command.external_event_id,
        "service_principal_ref": command.actor.service_ref,
        "model_name": command.model_name,
        "model_version": command.model_version,
        "detected_at": command.detected_at.astimezone(UTC).isoformat(),
        "processing_outcome": command.processing_outcome,
        "confidence": str(command.confidence) if command.confidence is not None else None,
        "payload_sha256": command.payload_sha256,
        "metadata_schema_version": command.metadata_schema_version,
        "auxiliary_metadata": command.auxiliary_metadata or {},
    }


def _semantic_digest(command: DetectionEventCommand) -> str:
    encoded = json.dumps(_normalized_payload(command), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_detection_provenance(command: DetectionEventCommand) -> str:
    if not all(
        value and value.strip()
        for value in (command.external_event_id, command.model_name, command.model_version)
    ):
        raise BusinessRuleViolation("Event identity and model provenance are required.")
    if command.detected_at.tzinfo is None or command.detected_at.utcoffset() is None:
        raise BusinessRuleViolation("Detection timestamp must include a timezone.")
    if command.processing_outcome not in EventProcessingOutcome.values:
        raise BusinessRuleViolation("Unsupported detection outcome.")
    if command.confidence is not None and not Decimal("0") <= command.confidence <= Decimal("1"):
        raise BusinessRuleViolation("Confidence must be between zero and one.")
    if command.metadata_schema_version < 1:
        raise BusinessRuleViolation("Metadata schema version must be positive.")
    if command.metadata_schema_version > 32767:
        raise BusinessRuleViolation("Metadata schema version exceeds the supported range.")
    if command.auxiliary_metadata is not None and not isinstance(command.auxiliary_metadata, dict):
        raise BusinessRuleViolation("Detection metadata must be a JSON object.")
    if command.payload_sha256 is not None and (
        len(command.payload_sha256) != 64
        or any(character not in "0123456789abcdef" for character in command.payload_sha256)
    ):
        raise BusinessRuleViolation("Payload digest must be a lowercase SHA-256 value.")
    metadata = command.auxiliary_metadata or {}
    pending = [(metadata, 0)]
    visited = 0
    while pending:
        node, depth = pending.pop()
        visited += 1
        if depth > 16 or visited > 4096:
            raise BusinessRuleViolation("Detection metadata exceeds the v1 complexity limit.")
        if isinstance(node, dict):
            for key, nested in node.items():
                if not isinstance(key, str):
                    raise BusinessRuleViolation("Detection metadata keys must be strings.")
                if key.casefold() in _FORBIDDEN_EVENT_METADATA_KEYS:
                    raise BusinessRuleViolation(
                        "Detection metadata cannot carry backend authority fields."
                    )
                pending.append((nested, depth + 1))
        elif isinstance(node, list):
            pending.extend((nested, depth + 1) for nested in node)
    try:
        encoded_metadata = json.dumps(
            metadata, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
    except TypeError, ValueError, RecursionError:
        raise BusinessRuleViolation("Detection metadata must be JSON serializable.") from None
    if len(encoded_metadata.encode("utf-8")) > 16_384:
        raise BusinessRuleViolation("Detection metadata exceeds the 16 KiB limit.")
    return _semantic_digest(command)


def _matches(event: DetectionEvent, command: DetectionEventCommand, digest: str) -> bool:
    return (
        event.video_source_id == command.video_source_id
        and event.external_event_id == command.external_event_id
        and event.service_principal_ref == command.actor.service_ref
        and event.model_name == command.model_name
        and event.model_version == command.model_version
        and event.detected_at == command.detected_at
        and event.processing_outcome == command.processing_outcome
        and event.confidence == command.confidence
        and event.metadata_schema_version == command.metadata_schema_version
        and event.auxiliary_metadata == (command.auxiliary_metadata or {})
        and event.payload_sha256 == (command.payload_sha256 or digest)
    )


def ingest_detection_event(
    command: DetectionEventCommand,
    *,
    policy: AuthorizationPolicy | None = None,
) -> DetectionEvent:
    actor = command.actor
    try:
        require_ai_service(actor)
        # Ingestion authority is established by the authenticated AI_SERVICE identity and
        # the locked VideoSource authorization state.  No unresolved human role policy is
        # needed to accept this machine command.
        if policy is not None:
            require_authorized(policy, "detection.ingest", actor)
        digest = validate_detection_provenance(command)
        try:
            with transaction.atomic():
                source = (
                    VideoSource.objects.select_for_update()
                    .filter(pk=command.video_source_id)
                    .first()
                )
                if source is None:
                    raise ResourceNotFound("Video source was not found.")
                validate_source_for_ingestion(source)
                existing = DetectionEvent.objects.filter(
                    video_source=source,
                    external_event_id=command.external_event_id,
                ).first()
                if existing is not None:
                    if not _matches(existing, command, digest):
                        raise IdempotencyConflict(
                            "Event identity was already accepted with different content."
                        )
                    record_successful_action(
                        actor=actor,
                        action="DETECTION_EVENT_REPLAYED",
                        resource_type="DETECTION_EVENT",
                        resource_id=existing.pk,
                        safe_context={
                            "source_id": source.pk,
                            "event_id": command.external_event_id,
                        },
                    )
                    return existing
                event = DetectionEvent.objects.create(
                    video_source=source,
                    external_event_id=command.external_event_id,
                    service_principal_ref=actor.service_ref,
                    model_name=command.model_name,
                    model_version=command.model_version,
                    detected_at=command.detected_at,
                    processing_outcome=command.processing_outcome,
                    confidence=command.confidence,
                    payload_sha256=command.payload_sha256 or digest,
                    metadata_schema_version=command.metadata_schema_version,
                    auxiliary_metadata=command.auxiliary_metadata or {},
                )
                record_successful_action(
                    actor=actor,
                    action="DETECTION_EVENT_ACCEPTED",
                    resource_type="DETECTION_EVENT",
                    resource_id=event.pk,
                    safe_context={
                        "source_id": source.pk,
                        "event_id": command.external_event_id,
                        "model_name": command.model_name,
                        "model_version": command.model_version,
                    },
                )
                return event
        except IntegrityError:
            existing = DetectionEvent.objects.filter(
                video_source_id=command.video_source_id,
                external_event_id=command.external_event_id,
            ).first()
            if existing and _matches(existing, command, digest):
                return existing
            raise IdempotencyConflict("Event identity conflicts with an accepted event.") from None
    except AuthorizationDenied, IdempotencyConflict:
        record_denied_action(
            actor=actor,
            action="DETECTION_EVENT_DENIED",
            resource_type="VIDEO_SOURCE",
            resource_id=command.video_source_id,
            safe_context={"event_id": command.external_event_id},
        )
        raise


def get_detection_event(
    event_id: UUID,
    *,
    actor: Actor,
    policy: AuthorizationPolicy | None = None,
) -> DetectionEvent:
    require_known_actor(actor)
    event = DetectionEvent.objects.select_related("video_source").filter(pk=event_id).first()
    if event is None:
        raise ResourceNotFound("Detection event was not found.")
    try:
        require_authorized(policy, "detection.read", actor, event)
    except AuthorizationDenied, PolicyNotConfigured:
        record_denied_action(
            actor=actor,
            action="DOMAIN_ACTION_DENIED",
            resource_type="DETECTION_EVENT",
            resource_id=event.pk,
            safe_context={"reason_code": "detection.read"},
        )
        raise
    return event
