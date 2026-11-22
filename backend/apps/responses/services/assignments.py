"""Transactional response assignment transitions with target membership checks."""

from uuid import UUID

from django.db import IntegrityError, transaction

from apps.audit.services import record_denied_action, record_successful_action
from apps.incidents.models import AccidentIncident, IncidentStatus
from apps.incidents.services.lifecycle import _mark_response_active_locked
from apps.organizations.models import Organization, OrganizationKind
from apps.responses.models import (
    AssignmentStatus,
    AssignmentStatusHistory,
    Response,
    ResponseActivityKind,
    ResponseAssignment,
)
from common.domain.actors import Actor
from common.domain.authorization import require_human, require_membership
from common.domain.exceptions import (
    AuthorizationDenied,
    IdempotencyConflict,
    InvalidStateTransition,
    PolicyNotConfigured,
    ResourceConflict,
    ResourceNotFound,
)
from common.domain.policies import AuthorizationPolicy, require_authorized
from common.domain.results import CommandResult

_TRANSITIONS = {
    AssignmentStatus.PENDING: {
        AssignmentStatus.ACKNOWLEDGED,
        AssignmentStatus.UNABLE_TO_RESPOND,
        AssignmentStatus.CANCELLED,
    },
    AssignmentStatus.ACKNOWLEDGED: {
        AssignmentStatus.IN_PROGRESS,
        AssignmentStatus.COMPLETED,
        AssignmentStatus.UNABLE_TO_RESPOND,
        AssignmentStatus.CANCELLED,
    },
    AssignmentStatus.IN_PROGRESS: {
        AssignmentStatus.COMPLETED,
        AssignmentStatus.UNABLE_TO_RESPOND,
        AssignmentStatus.CANCELLED,
    },
}


def _audit_denied(actor: Actor, assignment_id: UUID | None, reason: str) -> None:
    record_denied_action(
        actor=actor,
        action="DOMAIN_ACTION_DENIED",
        resource_type="ASSIGNMENT",
        resource_id=assignment_id,
        safe_context={"reason_code": reason},
    )


def _eligible_target(target: Organization) -> bool:
    return target.is_active and target.organization_kind in {
        OrganizationKind.POLICE,
        OrganizationKind.HOSPITAL,
    }


def _require_response_update_policy(assignment: ResponseAssignment) -> None:
    if assignment.target_organization.organization_kind == OrganizationKind.HOSPITAL:
        raise PolicyNotConfigured(
            "Hospital response update authority and lifecycle are not approved."
        )


def create_assignment(
    *,
    incident_id: UUID,
    target_organization_id: UUID,
    actor: Actor,
    command_id: UUID,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[ResponseAssignment]:
    try:
        user = require_human(actor)
        with transaction.atomic():
            incident = AccidentIncident.objects.select_for_update().filter(pk=incident_id).first()
            if incident is None:
                raise ResourceNotFound("Incident was not found.")
            target = (
                Organization.objects.select_for_update().filter(pk=target_organization_id).first()
            )
            if target is None:
                raise ResourceNotFound("Target organization was not found.")
            require_authorized(policy, "assignment.create", actor, (incident, target))
            existing = ResponseAssignment.objects.filter(creation_command_id=command_id).first()
            if existing:
                if (
                    existing.incident_id != incident.pk
                    or existing.target_organization_id != target.pk
                    or existing.assigned_by_user_id != user.pk
                ):
                    raise IdempotencyConflict("Assignment command identifier has different intent.")
                return CommandResult(existing, replayed=True)
            if incident.status not in {IncidentStatus.OPEN, IncidentStatus.RESPONSE_ACTIVE}:
                raise InvalidStateTransition("Assignments can only be added to active incidents.")
            if not _eligible_target(target):
                raise AuthorizationDenied(
                    "The target must be an active Police or Hospital organization."
                )
            assignment = ResponseAssignment.objects.create(
                incident=incident,
                target_organization=target,
                assigned_by_user=user,
                creation_command_id=command_id,
                status=AssignmentStatus.PENDING,
            )
            AssignmentStatusHistory.objects.create(
                response_assignment=assignment,
                from_status=None,
                to_status=AssignmentStatus.PENDING,
                changed_by_user=user,
                command_id=command_id,
            )
            record_successful_action(
                actor=actor,
                action="ASSIGNMENT_CREATED",
                resource_type="ASSIGNMENT",
                resource_id=assignment.pk,
                safe_context={
                    "command_id": command_id,
                    "incident_id": incident.pk,
                    "organization_id": target.pk,
                },
            )
            return CommandResult(assignment)
    except (
        AuthorizationDenied,
        PolicyNotConfigured,
        InvalidStateTransition,
        IdempotencyConflict,
    ):
        _audit_denied(actor, None, "assignment.create")
        raise
    except IntegrityError as exc:
        _audit_denied(actor, None, "assignment.create.conflict")
        raise ResourceConflict("An active assignment already exists for this target.") from exc


def _locked_assignment(assignment_id: UUID) -> tuple[AccidentIncident, ResponseAssignment]:
    assignment_ref = (
        ResponseAssignment.objects.filter(pk=assignment_id).values("incident_id").first()
    )
    if assignment_ref is None:
        raise ResourceNotFound("Assignment was not found.")
    incident = (
        AccidentIncident.objects.select_for_update()
        .filter(pk=assignment_ref["incident_id"])
        .first()
    )
    if incident is None:
        raise ResourceNotFound("Incident was not found.")
    assignment = (
        ResponseAssignment.objects.select_for_update()
        .select_related("target_organization")
        .filter(pk=assignment_id)
        .first()
    )
    if assignment is None:
        raise ResourceNotFound("Assignment was not found.")
    return incident, assignment


def _prior_history(
    *,
    command_id: UUID,
    assignment: ResponseAssignment,
    actor_id: UUID,
    target_status: str,
    reason: str | None,
    activity_kind: str | None,
    details: str | None,
) -> ResponseAssignment | None:
    prior = AssignmentStatusHistory.objects.filter(command_id=command_id).first()
    if prior is None:
        if Response.objects.filter(command_id=command_id).exists():
            raise IdempotencyConflict(
                "Assignment command identifier was used for another activity."
            )
        return None
    if (
        prior.response_assignment_id != assignment.pk
        or prior.to_status != target_status
        or prior.changed_by_user_id != actor_id
        or prior.reason != reason
    ):
        raise IdempotencyConflict("Assignment command identifier has different intent.")
    prior_response = Response.objects.filter(command_id=command_id).first()
    if activity_kind is None:
        if prior_response is not None:
            raise IdempotencyConflict("Assignment command identifier has different intent.")
    elif (
        prior_response is None
        or prior_response.response_assignment_id != assignment.pk
        or prior_response.actor_user_id != actor_id
        or prior_response.activity_kind != activity_kind
        or prior_response.details != details
    ):
        raise IdempotencyConflict("Assignment command identifier has different intent.")
    return assignment


def _transition_assignment(
    *,
    assignment_id: UUID,
    actor: Actor,
    command_id: UUID,
    to_status: str,
    reason: str | None = None,
    activity_kind: str | None = None,
    details: str | None = None,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[ResponseAssignment]:
    operation = {
        AssignmentStatus.ACKNOWLEDGED: "assignment.acknowledge",
        AssignmentStatus.IN_PROGRESS: "assignment.respond",
        AssignmentStatus.COMPLETED: "assignment.respond",
        AssignmentStatus.UNABLE_TO_RESPOND: "assignment.respond",
        AssignmentStatus.CANCELLED: "assignment.cancel",
    }[to_status]
    try:
        user = require_human(actor)
        with transaction.atomic():
            incident, assignment = _locked_assignment(assignment_id)
            if assignment.target_organization.organization_kind == OrganizationKind.HOSPITAL:
                require_membership(
                    actor,
                    assignment.target_organization,
                    expected_role=assignment.target_organization.organization_kind,
                )
                _require_response_update_policy(assignment)
            else:
                if to_status == AssignmentStatus.CANCELLED:
                    require_authorized(policy, operation, actor, assignment)
                require_membership(
                    actor,
                    assignment.target_organization,
                    expected_role=assignment.target_organization.organization_kind,
                )
            if to_status == AssignmentStatus.IN_PROGRESS:
                activity_kind = ResponseActivityKind.PROGRESS_UPDATE
            prior = _prior_history(
                command_id=command_id,
                assignment=assignment,
                actor_id=user.pk,
                target_status=to_status,
                reason=reason.strip() if reason else None,
                activity_kind=activity_kind,
                details=details,
            )
            if prior:
                return CommandResult(prior, replayed=True)
            if incident.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
                raise InvalidStateTransition("A closed or resolved incident cannot be updated.")
            if to_status not in _TRANSITIONS.get(assignment.status, set()):
                raise InvalidStateTransition(
                    f"Assignment cannot move from {assignment.status} to {to_status}."
                )
            old_status = assignment.status
            assignment.status = to_status
            assignment.save(update_fields=["status", "updated_at"])
            AssignmentStatusHistory.objects.create(
                response_assignment=assignment,
                from_status=old_status,
                to_status=to_status,
                changed_by_user=user,
                reason=reason.strip() if reason else None,
                command_id=command_id,
            )
            if activity_kind:
                Response.objects.create(
                    response_assignment=assignment,
                    actor_user=user,
                    activity_kind=activity_kind,
                    details=details,
                    command_id=command_id,
                )
            if to_status == AssignmentStatus.IN_PROGRESS:
                _mark_response_active_locked(
                    incident=incident,
                    actor=actor,
                    command_id=command_id,
                )
            action = {
                AssignmentStatus.ACKNOWLEDGED: "ASSIGNMENT_ACKNOWLEDGED",
                AssignmentStatus.IN_PROGRESS: "ASSIGNMENT_STARTED",
                AssignmentStatus.COMPLETED: "ASSIGNMENT_COMPLETED",
                AssignmentStatus.UNABLE_TO_RESPOND: "ASSIGNMENT_UNABLE_TO_RESPOND",
                AssignmentStatus.CANCELLED: "ASSIGNMENT_CANCELLED",
            }[to_status]
            record_successful_action(
                actor=actor,
                action=action,
                resource_type="ASSIGNMENT",
                resource_id=assignment.pk,
                safe_context={
                    "command_id": command_id,
                    "from_status": old_status,
                    "to_status": to_status,
                    "incident_id": incident.pk,
                    "organization_id": assignment.target_organization_id,
                },
            )
            return CommandResult(assignment)
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, IdempotencyConflict:
        _audit_denied(actor, assignment_id, operation)
        raise
    except IntegrityError as exc:
        _audit_denied(actor, assignment_id, "assignment.transition.conflict")
        raise ResourceConflict("Assignment transition conflicts with existing history.") from exc


def acknowledge_assignment(
    *, assignment_id: UUID, actor: Actor, command_id: UUID, policy=None
) -> CommandResult[ResponseAssignment]:
    return _transition_assignment(
        assignment_id=assignment_id,
        actor=actor,
        command_id=command_id,
        to_status=AssignmentStatus.ACKNOWLEDGED,
        policy=policy,
    )


def start_response(
    *, assignment_id: UUID, actor: Actor, command_id: UUID, details: str = "", policy=None
) -> CommandResult[ResponseAssignment]:
    normalized_details = details.strip() or None
    if normalized_details is not None and len(normalized_details) > 2000:
        raise InvalidStateTransition("Response details are too long.")
    return _transition_assignment(
        assignment_id=assignment_id,
        actor=actor,
        command_id=command_id,
        to_status=AssignmentStatus.IN_PROGRESS,
        activity_kind=ResponseActivityKind.PROGRESS_UPDATE,
        details=normalized_details,
        policy=policy,
    )


def complete_assignment(
    *, assignment_id: UUID, actor: Actor, command_id: UUID, details: str, policy=None
) -> CommandResult[ResponseAssignment]:
    if not details or not details.strip():
        raise InvalidStateTransition("Completion details are required.")
    if len(details.strip()) > 2000:
        raise InvalidStateTransition("Completion details are too long.")
    return _transition_assignment(
        assignment_id=assignment_id,
        actor=actor,
        command_id=command_id,
        to_status=AssignmentStatus.COMPLETED,
        activity_kind=ResponseActivityKind.COMPLETION_NOTE,
        details=details.strip(),
        policy=policy,
    )


def mark_unable_to_respond(
    *, assignment_id: UUID, actor: Actor, command_id: UUID, reason: str, policy=None
) -> CommandResult[ResponseAssignment]:
    if not reason or not reason.strip():
        raise InvalidStateTransition("A reason is required when unable to respond.")
    if len(reason.strip()) > 2000:
        raise InvalidStateTransition("The reason is too long.")
    return _transition_assignment(
        assignment_id=assignment_id,
        actor=actor,
        command_id=command_id,
        to_status=AssignmentStatus.UNABLE_TO_RESPOND,
        reason=reason.strip(),
        activity_kind=ResponseActivityKind.UNABLE_TO_RESPOND_NOTE,
        details=reason.strip(),
        policy=policy,
    )


def cancel_assignment(
    *, assignment_id: UUID, actor: Actor, command_id: UUID, reason: str, policy=None
) -> CommandResult[ResponseAssignment]:
    if not reason or not reason.strip():
        raise InvalidStateTransition("A cancellation reason is required.")
    return _transition_assignment(
        assignment_id=assignment_id,
        actor=actor,
        command_id=command_id,
        to_status=AssignmentStatus.CANCELLED,
        reason=reason.strip(),
        policy=policy,
    )


def record_response_activity(
    *,
    assignment_id: UUID,
    actor: Actor,
    command_id: UUID,
    activity_kind: str,
    details: str | None = None,
) -> CommandResult[Response]:
    try:
        user = require_human(actor)
        normalized_details = details.strip() if details and details.strip() else None
        if normalized_details is not None and len(normalized_details) > 2000:
            raise InvalidStateTransition("Response details are too long.")
        with transaction.atomic():
            incident, assignment = _locked_assignment(assignment_id)
            require_membership(actor, assignment.target_organization)
            _require_response_update_policy(assignment)
            prior = Response.objects.filter(command_id=command_id).first()
            if prior:
                if (
                    prior.response_assignment_id != assignment.pk
                    or prior.actor_user_id != user.pk
                    or prior.activity_kind != activity_kind
                    or prior.details != normalized_details
                ):
                    raise IdempotencyConflict("Response command identifier has different intent.")
                return CommandResult(prior, replayed=True)
            if assignment.status not in {
                AssignmentStatus.ACKNOWLEDGED,
                AssignmentStatus.IN_PROGRESS,
            }:
                raise InvalidStateTransition("Response activity requires an active assignment.")
            if incident.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
                raise InvalidStateTransition("The incident is not active.")
            allowed = {
                "POLICE": {
                    ResponseActivityKind.PROGRESS_UPDATE,
                    ResponseActivityKind.GENERAL_NOTE,
                },
                "HOSPITAL": {
                    ResponseActivityKind.READINESS_UPDATE,
                    ResponseActivityKind.GENERAL_NOTE,
                },
            }
            if activity_kind not in allowed.get(
                assignment.target_organization.organization_kind, set()
            ):
                raise InvalidStateTransition("Activity kind does not match the organization role.")
            response = Response.objects.create(
                response_assignment=assignment,
                actor_user=user,
                activity_kind=activity_kind,
                details=normalized_details,
                command_id=command_id,
            )
            record_successful_action(
                actor=actor,
                action="ASSIGNMENT_ACTIVITY_RECORDED",
                resource_type="ASSIGNMENT",
                resource_id=assignment.pk,
                safe_context={
                    "command_id": command_id,
                    "organization_id": assignment.target_organization_id,
                },
            )
            return CommandResult(response)
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, IdempotencyConflict:
        _audit_denied(actor, assignment_id, "assignment.activity")
        raise
    except IntegrityError as exc:
        _audit_denied(actor, assignment_id, "assignment.activity.conflict")
        raise ResourceConflict("Response activity conflicts with an existing command.") from exc


def reassign_assignment(
    *,
    assignment_id: UUID,
    target_organization_id: UUID,
    actor: Actor,
    command_id: UUID,
    reason: str,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[ResponseAssignment]:
    try:
        user = require_human(actor)
        if not reason or not reason.strip():
            raise InvalidStateTransition("A reassignment reason is required.")
        with transaction.atomic():
            incident, old = _locked_assignment(assignment_id)
            target = (
                Organization.objects.select_for_update().filter(pk=target_organization_id).first()
            )
            if target is None:
                raise ResourceNotFound("Target organization was not found.")
            require_authorized(policy, "assignment.reassign", actor, (old, target))
            prior = ResponseAssignment.objects.filter(creation_command_id=command_id).first()
            if prior:
                prior_cancel = AssignmentStatusHistory.objects.filter(
                    command_id=command_id,
                    response_assignment=old,
                    to_status=AssignmentStatus.CANCELLED,
                ).first()
                if (
                    prior.replacement_for_id != old.pk
                    or prior.target_organization_id != target.pk
                    or prior.assigned_by_user_id != user.pk
                    or prior.incident_id != incident.pk
                    or prior_cancel is None
                    or prior_cancel.changed_by_user_id != user.pk
                    or prior_cancel.reason != reason.strip()
                ):
                    raise IdempotencyConflict(
                        "Reassignment command identifier has different intent."
                    )
                return CommandResult(prior, replayed=True)
            if old.status not in _TRANSITIONS:
                raise InvalidStateTransition("The assignment is already terminal.")
            if target.pk == old.target_organization_id or not _eligible_target(target):
                raise InvalidStateTransition(
                    "Reassignment requires a different active eligible target."
                )
            if incident.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
                raise InvalidStateTransition("A resolved incident cannot be reassigned.")
            old_status = old.status
            old.status = AssignmentStatus.CANCELLED
            old.save(update_fields=["status", "updated_at"])
            AssignmentStatusHistory.objects.create(
                response_assignment=old,
                from_status=old_status,
                to_status=AssignmentStatus.CANCELLED,
                changed_by_user=user,
                reason=reason.strip(),
                command_id=command_id,
            )
            replacement = ResponseAssignment.objects.create(
                incident=incident,
                target_organization=target,
                assigned_by_user=user,
                replacement_for=old,
                creation_command_id=command_id,
                status=AssignmentStatus.PENDING,
            )
            AssignmentStatusHistory.objects.create(
                response_assignment=replacement,
                from_status=None,
                to_status=AssignmentStatus.PENDING,
                changed_by_user=user,
                reason=reason.strip(),
            )
            record_successful_action(
                actor=actor,
                action="ASSIGNMENT_REASSIGNED",
                resource_type="ASSIGNMENT",
                resource_id=replacement.pk,
                safe_context={
                    "command_id": command_id,
                    "assignment_id": old.pk,
                    "incident_id": incident.pk,
                    "organization_id": target.pk,
                },
            )
            return CommandResult(replacement)
    except (
        AuthorizationDenied,
        PolicyNotConfigured,
        InvalidStateTransition,
        IdempotencyConflict,
    ):
        _audit_denied(actor, assignment_id, "assignment.reassign")
        raise
    except IntegrityError as exc:
        _audit_denied(actor, assignment_id, "assignment.reassign.conflict")
        raise ResourceConflict("Reassignment conflicts with an active target assignment.") from exc
