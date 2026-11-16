"""Locked incident transitions and resolution/closure policy hooks."""

from uuid import UUID

from django.db import transaction

from apps.audit.services import record_denied_action, record_successful_action
from apps.incidents.models import AccidentIncident, IncidentStatus, IncidentStatusHistory
from apps.responses.models import AssignmentStatus, ResponseAssignment
from common.domain.actors import Actor, HumanActor
from common.domain.authorization import require_human, require_known_actor
from common.domain.exceptions import (
    AuthorizationDenied,
    IdempotencyConflict,
    InvalidStateTransition,
    PolicyNotConfigured,
    ResourceNotFound,
)
from common.domain.policies import AuthorizationPolicy, require_authorized
from common.domain.results import CommandResult

_ASSIGNMENT_TERMINAL = {
    AssignmentStatus.COMPLETED,
    AssignmentStatus.UNABLE_TO_RESPOND,
    AssignmentStatus.CANCELLED,
}


def _audit_denied(actor: Actor, incident_id: UUID, operation: str) -> None:
    record_denied_action(
        actor=actor,
        action="DOMAIN_ACTION_DENIED",
        resource_type="INCIDENT",
        resource_id=incident_id,
        safe_context={"reason_code": operation},
    )


def get_incident(
    incident_id: UUID, *, actor: Actor, policy: AuthorizationPolicy | None = None
) -> AccidentIncident:
    require_known_actor(actor)
    incident = AccidentIncident.objects.filter(pk=incident_id).first()
    if incident is None:
        raise ResourceNotFound("Incident was not found.")
    require_authorized(policy, "incident.read", actor, incident)
    return incident


def _mark_response_active_locked(
    *, incident: AccidentIncident, actor: Actor, command_id: UUID
) -> AccidentIncident:
    """Called by response services while holding the incident row lock."""

    if incident.status == IncidentStatus.RESPONSE_ACTIVE:
        return incident
    if incident.status != IncidentStatus.OPEN:
        raise InvalidStateTransition("Only open incidents can become response active.")
    prior = IncidentStatusHistory.objects.filter(command_id=command_id).first()
    if prior:
        if prior.incident_id == incident.pk and prior.to_status == IncidentStatus.RESPONSE_ACTIVE:
            return incident
        raise IdempotencyConflict("Incident transition command identifier has different intent.")
    incident.status = IncidentStatus.RESPONSE_ACTIVE
    incident.save(update_fields=["status", "updated_at"])
    user = require_human(actor) if isinstance(actor, HumanActor) else None
    service_ref = actor.service_ref if not isinstance(actor, HumanActor) else None
    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status=IncidentStatus.OPEN,
        to_status=IncidentStatus.RESPONSE_ACTIVE,
        changed_by_user=user,
        actor_service_ref=service_ref,
        command_id=command_id,
    )
    record_successful_action(
        actor=actor,
        action="INCIDENT_TRANSITIONED",
        resource_type="INCIDENT",
        resource_id=incident.pk,
        safe_context={
            "command_id": command_id,
            "from_status": IncidentStatus.OPEN,
            "to_status": IncidentStatus.RESPONSE_ACTIVE,
        },
    )
    return incident


def resolve_incident(
    *,
    incident_id: UUID,
    actor: Actor,
    command_id: UUID,
    reason: str,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[AccidentIncident]:
    try:
        user = require_human(actor)
        if not reason or not reason.strip():
            raise InvalidStateTransition("A resolution reason is required.")
        with transaction.atomic():
            incident = AccidentIncident.objects.select_for_update().filter(pk=incident_id).first()
            if incident is None:
                raise ResourceNotFound("Incident was not found.")
            require_authorized(policy, "incident.resolve", actor, incident)
            prior = IncidentStatusHistory.objects.filter(command_id=command_id).first()
            if prior:
                if (
                    prior.incident_id != incident.pk
                    or prior.to_status != IncidentStatus.RESOLVED
                    or prior.reason != reason.strip()
                    or prior.changed_by_user_id != user.pk
                ):
                    raise IdempotencyConflict("Incident command identifier has different intent.")
                return CommandResult(incident, replayed=True)
            if incident.status not in {IncidentStatus.OPEN, IncidentStatus.RESPONSE_ACTIVE}:
                raise InvalidStateTransition("Only open incidents can be resolved.")
            assignments = list(
                ResponseAssignment.objects.select_for_update()
                .filter(incident=incident)
                .order_by("pk")
            )
            if any(item.status not in _ASSIGNMENT_TERMINAL for item in assignments):
                raise InvalidStateTransition(
                    "All incident assignments must be terminal to resolve."
                )
            old_status = incident.status
            incident.status = IncidentStatus.RESOLVED
            incident.save(update_fields=["status", "updated_at"])
            IncidentStatusHistory.objects.create(
                incident=incident,
                from_status=old_status,
                to_status=IncidentStatus.RESOLVED,
                changed_by_user=user,
                reason=reason.strip(),
                command_id=command_id,
            )
            record_successful_action(
                actor=actor,
                action="INCIDENT_TRANSITIONED",
                resource_type="INCIDENT",
                resource_id=incident.pk,
                safe_context={
                    "command_id": command_id,
                    "from_status": old_status,
                    "to_status": IncidentStatus.RESOLVED,
                },
            )
            return CommandResult(incident)
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, IdempotencyConflict:
        _audit_denied(actor, incident_id, "incident.resolve")
        raise


def close_incident(
    *,
    incident_id: UUID,
    actor: Actor,
    command_id: UUID,
    reason: str,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[AccidentIncident]:
    try:
        user = require_human(actor)
        if not reason or not reason.strip():
            raise InvalidStateTransition("A closure reason is required.")
        with transaction.atomic():
            incident = AccidentIncident.objects.select_for_update().filter(pk=incident_id).first()
            if incident is None:
                raise ResourceNotFound("Incident was not found.")
            require_authorized(policy, "incident.close", actor, incident)
            prior = IncidentStatusHistory.objects.filter(command_id=command_id).first()
            if prior:
                if (
                    prior.incident_id != incident.pk
                    or prior.to_status != IncidentStatus.CLOSED
                    or prior.reason != reason.strip()
                    or prior.changed_by_user_id != user.pk
                ):
                    raise IdempotencyConflict("Incident command identifier has different intent.")
                return CommandResult(incident, replayed=True)
            if incident.status != IncidentStatus.RESOLVED:
                raise InvalidStateTransition("Only resolved incidents can be closed.")
            incident.status = IncidentStatus.CLOSED
            incident.save(update_fields=["status", "updated_at"])
            IncidentStatusHistory.objects.create(
                incident=incident,
                from_status=IncidentStatus.RESOLVED,
                to_status=IncidentStatus.CLOSED,
                changed_by_user=user,
                reason=reason.strip(),
                command_id=command_id,
            )
            record_successful_action(
                actor=actor,
                action="INCIDENT_TRANSITIONED",
                resource_type="INCIDENT",
                resource_id=incident.pk,
                safe_context={
                    "command_id": command_id,
                    "from_status": IncidentStatus.RESOLVED,
                    "to_status": IncidentStatus.CLOSED,
                },
            )
            return CommandResult(incident)
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, IdempotencyConflict:
        _audit_denied(actor, incident_id, "incident.close")
        raise


def transition_incident(
    *,
    incident_id: UUID,
    to_status: str,
    actor: Actor,
    command_id: UUID,
    reason: str = "",
    policy=None,
) -> CommandResult[AccidentIncident]:
    """Public lifecycle command; RESPONSE_ACTIVE is owned by response activity services."""

    if to_status == IncidentStatus.RESOLVED:
        return resolve_incident(
            incident_id=incident_id,
            actor=actor,
            command_id=command_id,
            reason=reason,
            policy=policy,
        )
    if to_status == IncidentStatus.CLOSED:
        return close_incident(
            incident_id=incident_id,
            actor=actor,
            command_id=command_id,
            reason=reason,
            policy=policy,
        )
    _audit_denied(actor, incident_id, "incident.transition")
    raise InvalidStateTransition("This incident transition is not an external command.")
