"""Safe, append-oriented business audit events."""

from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.audit.models import AuditEvent
from common.domain.actors import Actor, AnonymousActor, HumanActor, MachineActor
from common.domain.exceptions import BusinessRuleViolation

_SAFE_CONTEXT_KEYS = frozenset(
    {
        "command_id",
        "request_id",
        "reason_code",
        "from_status",
        "to_status",
        "source_id",
        "event_id",
        "candidate_id",
        "incident_id",
        "assignment_id",
        "organization_id",
        "membership_id",
        "evidence_id",
        "location_id",
        "notification_id",
        "message_code",
        "failure_code",
        "attempt_number",
        "association_method",
        "model_name",
        "model_version",
        "count",
        "policy_ref",
        "simulated",
    }
)

_ACTIONS = frozenset(
    {
        "DETECTION_EVENT_ACCEPTED",
        "DETECTION_EVENT_REPLAYED",
        "DETECTION_EVENT_DENIED",
        "CANDIDATE_CREATED",
        "CANDIDATE_EVENT_ASSOCIATED",
        "CANDIDATE_REVIEW_STARTED",
        "CANDIDATE_VERIFIED",
        "CANDIDATE_REJECTED",
        "INCIDENT_TRANSITIONED",
        "ASSIGNMENT_CREATED",
        "ASSIGNMENT_ACKNOWLEDGED",
        "ASSIGNMENT_STARTED",
        "ASSIGNMENT_ACTIVITY_RECORDED",
        "ASSIGNMENT_COMPLETED",
        "ASSIGNMENT_UNABLE_TO_RESPOND",
        "ASSIGNMENT_CANCELLED",
        "ASSIGNMENT_REASSIGNED",
        "MEMBERSHIP_ACTIVATED",
        "MEMBERSHIP_SUSPENDED",
        "MEMBERSHIP_REVOKED",
        "VIDEO_SOURCE_REGISTERED",
        "VIDEO_SOURCE_AUTHORIZED",
        "VIDEO_SOURCE_SUSPENDED",
        "VIDEO_SOURCE_REVOKED",
        "EVIDENCE_CREATED",
        "EVIDENCE_UPLOAD_SESSION_CREATED",
        "EVIDENCE_UPLOAD_AUTHORIZED",
        "EVIDENCE_UPLOAD_COMPLETED",
        "EVIDENCE_UPLOAD_FAILED",
        "EVIDENCE_VALIDATED",
        "EVIDENCE_AVAILABLE",
        "EVIDENCE_ACCESS_GRANTED",
        "EVIDENCE_ACCESS_DENIED",
        "EVIDENCE_EXPIRED",
        "EVIDENCE_DELETED",
        "LOCATION_CREATED",
        "LOCATION_VERIFIED",
        "LOCATION_CORRECTED",
        "NOTIFICATION_CREATED",
        "NOTIFICATION_PENDING",
        "NOTIFICATION_DELIVERY_SIMULATED",
        "NOTIFICATION_DELIVERY_FAILED",
        "NOTIFICATION_READ",
        "NOTIFICATION_CANCELLED",
        "DOMAIN_ACTION_DENIED",
        "DOMAIN_ACTION_FAILED",
    }
)


def _safe_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    raise BusinessRuleViolation("Audit context contains an unsupported value.")


def _actor_fields(actor: Actor | None) -> dict[str, object]:
    if actor is None or isinstance(actor, AnonymousActor):
        return {
            "actor_user": None,
            "actor_kind": AuditEvent.ActorKind.ANONYMOUS,
            "actor_service_ref": None,
            "actor_ref_snapshot": "ANONYMOUS",
        }
    if isinstance(actor, HumanActor):
        return {
            "actor_user_id": actor.user_id
            if get_user_model().objects.filter(pk=actor.user_id).exists()
            else None,
            "actor_kind": AuditEvent.ActorKind.HUMAN,
            "actor_service_ref": None,
            "actor_ref_snapshot": str(actor.user_id),
        }
    if isinstance(actor, MachineActor):
        return {
            "actor_user": None,
            "actor_kind": AuditEvent.ActorKind.MACHINE,
            "actor_service_ref": actor.service_ref,
            "actor_ref_snapshot": actor.service_ref,
        }
    raise BusinessRuleViolation("Unsupported audit actor.")


def record_audit_event(
    *,
    actor: Actor | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    outcome: str = AuditEvent.Outcome.SUCCESS,
    request_id: UUID | None = None,
    safe_context: dict[str, object] | None = None,
) -> AuditEvent:
    """Insert one allow-listed audit event without retaining request payloads."""

    if action not in _ACTIONS:
        raise BusinessRuleViolation("Audit action is not allow-listed.")
    if resource_type not in AuditEvent.ResourceType.values:
        raise BusinessRuleViolation("Audit resource type is not approved.")
    raw_context = safe_context or {}
    if set(raw_context) - _SAFE_CONTEXT_KEYS:
        raise BusinessRuleViolation("Audit context contains an unapproved key.")
    context = {key: _safe_value(value) for key, value in raw_context.items()}
    return AuditEvent.objects.create(
        **_actor_fields(actor),
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        outcome=outcome,
        request_id=request_id,
        safe_context=context,
    )


def record_successful_action(**kwargs: object) -> AuditEvent:
    kwargs["outcome"] = AuditEvent.Outcome.SUCCESS
    return record_audit_event(**kwargs)  # type: ignore[arg-type]


def record_denied_action(**kwargs: object) -> AuditEvent:
    """Persist a denial in its own transaction after the business transaction exits."""

    kwargs["outcome"] = AuditEvent.Outcome.DENIED
    with transaction.atomic():
        return record_audit_event(**kwargs)  # type: ignore[arg-type]


def record_failed_action(**kwargs: object) -> AuditEvent:
    kwargs["outcome"] = AuditEvent.Outcome.FAILED
    with transaction.atomic():
        return record_audit_event(**kwargs)  # type: ignore[arg-type]
