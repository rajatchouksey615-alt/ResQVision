"""Policy-gated simulated notification state; no external delivery is performed."""

import re
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record_denied_action, record_successful_action
from apps.incidents.models import AccidentIncident
from apps.notifications.models import (
    DeliveryOutcome,
    Notification,
    NotificationDeliveryAttempt,
    NotificationStatus,
)
from apps.responses.models import AssignmentStatus, ResponseAssignment
from common.domain.actors import Actor, HumanActor
from common.domain.authorization import require_human, require_membership
from common.domain.exceptions import (
    AuthorizationDenied,
    BusinessRuleViolation,
    IdempotencyConflict,
    InvalidStateTransition,
    PolicyNotConfigured,
    ResourceConflict,
    ResourceNotFound,
)
from common.domain.policies import AuthorizationPolicy, require_authorized
from common.domain.results import CommandResult

_SAFE_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,63}$")


def _audit_denied(actor: Actor, notification_id: UUID | None, operation: str) -> None:
    record_denied_action(
        actor=actor,
        action="DOMAIN_ACTION_DENIED",
        resource_type="NOTIFICATION",
        resource_id=notification_id,
        safe_context={"reason_code": operation},
    )


def _audit_command(command_id: UUID) -> AuditEvent | None:
    return AuditEvent.objects.filter(safe_context__command_id=str(command_id)).first()


def _assert_command_intent(
    *,
    prior: AuditEvent,
    notification: Notification,
    actor_id: UUID,
    action: str,
    expected_context: dict[str, object],
) -> None:
    if (
        prior.resource_type != AuditEvent.ResourceType.NOTIFICATION
        or prior.resource_id != notification.pk
        or prior.action != action
        or prior.actor_user_id != actor_id
    ):
        raise IdempotencyConflict("Notification command identifier has different intent.")
    for key, value in expected_context.items():
        if prior.safe_context.get(key) != value:
            raise IdempotencyConflict("Notification command identifier has different intent.")


def _locked_notification(notification_id: UUID) -> Notification:
    notification = Notification.objects.select_for_update().filter(pk=notification_id).first()
    if notification is None:
        raise ResourceNotFound("Notification was not found.")
    return notification


def _lock_assignment(assignment_id: UUID) -> ResponseAssignment:
    ref = ResponseAssignment.objects.filter(pk=assignment_id).values("incident_id").first()
    if ref is None:
        raise ResourceNotFound("Assignment was not found.")
    # Keep the global lock order consistent with response and incident services.
    if not AccidentIncident.objects.select_for_update().filter(pk=ref["incident_id"]).exists():
        raise ResourceNotFound("Incident was not found.")
    assignment = (
        ResponseAssignment.objects.select_for_update()
        .select_related("target_organization")
        .filter(pk=assignment_id)
        .first()
    )
    if assignment is None:
        raise ResourceNotFound("Assignment was not found.")
    return assignment


def create_notification(
    *,
    actor: Actor,
    recipient_user_id: UUID,
    safe_message_code: str,
    command_id: UUID,
    incident_id: UUID | None = None,
    assignment_id: UUID | None = None,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[Notification]:
    """Create an approved, in-application notification record."""

    try:
        user = require_human(actor)
        if (incident_id is None) == (assignment_id is None):
            raise BusinessRuleViolation("Exactly one incident or assignment target is required.")
        if not _SAFE_CODE.fullmatch(safe_message_code):
            raise BusinessRuleViolation("A safe allow-listed message code is required.")
        prior_audit = _audit_command(command_id)
        existing = Notification.objects.filter(creation_command_id=command_id).first()
        if existing is not None:
            require_authorized(
                policy,
                "notification.create",
                actor,
                (existing.incident, existing.response_assignment, existing.recipient_user),
            )
            if (
                existing.recipient_user_id != recipient_user_id
                or existing.incident_id != incident_id
                or existing.response_assignment_id != assignment_id
                or existing.safe_message_code != safe_message_code
                or prior_audit is None
            ):
                raise IdempotencyConflict("Notification command identifier has different intent.")
            _assert_command_intent(
                prior=prior_audit,
                notification=existing,
                actor_id=user.pk,
                action="NOTIFICATION_CREATED",
                expected_context={
                    "command_id": str(command_id),
                    "message_code": safe_message_code,
                },
            )
            return CommandResult(existing, replayed=True)
        if prior_audit is not None:
            raise IdempotencyConflict("Notification command identifier has different intent.")

        recipient = get_user_model().objects.filter(pk=recipient_user_id, is_active=True).first()
        if recipient is None:
            raise ResourceNotFound("Notification recipient was not found.")
        with transaction.atomic():
            if incident_id is not None:
                incident = (
                    AccidentIncident.objects.select_for_update().filter(pk=incident_id).first()
                )
                if incident is None:
                    raise ResourceNotFound("Incident was not found.")
                assignment = None
            else:
                assignment = _lock_assignment(assignment_id)
                if assignment.status not in {
                    AssignmentStatus.PENDING,
                    AssignmentStatus.ACKNOWLEDGED,
                    AssignmentStatus.IN_PROGRESS,
                }:
                    raise InvalidStateTransition("Notifications require an active assignment.")
                require_membership(
                    HumanActor(recipient),
                    assignment.target_organization,
                )
                incident = None
            require_authorized(
                policy, "notification.create", actor, (incident, assignment, recipient)
            )
            notification = Notification.objects.create(
                recipient_user=recipient,
                incident=incident,
                response_assignment=assignment,
                creation_command_id=command_id,
                safe_message_code=safe_message_code,
                status=NotificationStatus.CREATED,
            )
            record_successful_action(
                actor=actor,
                action="NOTIFICATION_CREATED",
                resource_type="NOTIFICATION",
                resource_id=notification.pk,
                safe_context={"command_id": command_id, "message_code": safe_message_code},
            )
            return CommandResult(notification)
    except AuthorizationDenied, PolicyNotConfigured, IdempotencyConflict:
        _audit_denied(actor, None, "notification.create")
        raise
    except IntegrityError as exc:
        existing = Notification.objects.filter(creation_command_id=command_id).first()
        if existing is not None:
            prior_audit = _audit_command(command_id)
            if (
                prior_audit is not None
                and existing.recipient_user_id == recipient_user_id
                and existing.incident_id == incident_id
                and existing.response_assignment_id == assignment_id
                and existing.safe_message_code == safe_message_code
            ):
                _assert_command_intent(
                    prior=prior_audit,
                    notification=existing,
                    actor_id=user.pk,
                    action="NOTIFICATION_CREATED",
                    expected_context={
                        "command_id": str(command_id),
                        "message_code": safe_message_code,
                    },
                )
                return CommandResult(existing, replayed=True)
        _audit_denied(actor, None, "notification.create.conflict")
        raise ResourceConflict("Notification creation conflicts with an existing command.") from exc


def mark_notification_pending(
    *,
    notification_id: UUID,
    actor: Actor,
    command_id: UUID,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[Notification]:
    try:
        user = require_human(actor)
        with transaction.atomic():
            notification = _locked_notification(notification_id)
            require_authorized(policy, "notification.pending", actor, notification)
            prior = _audit_command(command_id)
            context = {"command_id": str(command_id), "to_status": NotificationStatus.PENDING}
            if prior:
                _assert_command_intent(
                    prior=prior,
                    notification=notification,
                    actor_id=user.pk,
                    action="NOTIFICATION_PENDING",
                    expected_context=context,
                )
                return CommandResult(notification, replayed=True)
            if notification.status == NotificationStatus.PENDING:
                record_successful_action(
                    actor=actor,
                    action="NOTIFICATION_PENDING",
                    resource_type="NOTIFICATION",
                    resource_id=notification.pk,
                    safe_context=context,
                )
                return CommandResult(notification)
            if notification.status not in {NotificationStatus.CREATED, NotificationStatus.FAILED}:
                raise InvalidStateTransition("Only created or failed notifications can be queued.")
            prior_status = notification.status
            notification.status = NotificationStatus.PENDING
            notification.save(update_fields=["status"])
            record_successful_action(
                actor=actor,
                action="NOTIFICATION_PENDING",
                resource_type="NOTIFICATION",
                resource_id=notification.pk,
                safe_context={
                    "command_id": command_id,
                    "from_status": prior_status,
                    "to_status": NotificationStatus.PENDING,
                },
            )
            return CommandResult(notification)
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, IdempotencyConflict:
        _audit_denied(actor, notification_id, "notification.pending")
        raise


def _record_delivery_outcome(
    *,
    notification_id: UUID,
    actor: Actor,
    command_id: UUID,
    outcome: str,
    failure_code: str | None,
    policy: AuthorizationPolicy | None,
) -> CommandResult[NotificationDeliveryAttempt]:
    action = (
        "NOTIFICATION_DELIVERY_SIMULATED"
        if outcome == DeliveryOutcome.DELIVERED_SIMULATED
        else "NOTIFICATION_DELIVERY_FAILED"
    )
    operation = "notification.deliver" if failure_code is None else "notification.fail"
    try:
        user = require_human(actor)
        if failure_code is not None and not _SAFE_CODE.fullmatch(failure_code):
            raise BusinessRuleViolation("A safe failure code is required.")
        with transaction.atomic():
            notification = _locked_notification(notification_id)
            require_authorized(policy, operation, actor, notification)
            prior = _audit_command(command_id)
            expected_context: dict[str, object] = {
                "command_id": str(command_id),
                "to_status": (
                    NotificationStatus.DELIVERED_SIMULATED
                    if outcome == DeliveryOutcome.DELIVERED_SIMULATED
                    else NotificationStatus.FAILED
                ),
                "failure_code": failure_code,
            }
            if prior:
                _assert_command_intent(
                    prior=prior,
                    notification=notification,
                    actor_id=user.pk,
                    action=action,
                    expected_context=expected_context,
                )
                attempt_number = prior.safe_context.get("attempt_number")
                attempt = NotificationDeliveryAttempt.objects.filter(
                    notification=notification,
                    attempt_number=attempt_number,
                    command_id=command_id,
                ).first()
                if attempt is None:
                    raise ResourceConflict("The original notification attempt is missing.")
                return CommandResult(attempt, replayed=True)
            if notification.status != NotificationStatus.PENDING:
                raise InvalidStateTransition(
                    "Only pending notifications can record a delivery attempt."
                )
            attempt_number = (
                NotificationDeliveryAttempt.objects.filter(notification=notification).aggregate(
                    maximum=Max("attempt_number")
                )["maximum"]
                or 0
            ) + 1
            attempt = NotificationDeliveryAttempt.objects.create(
                notification=notification,
                attempt_number=attempt_number,
                command_id=command_id,
                outcome=outcome,
                safe_failure_code=failure_code,
                attempted_at=timezone.now(),
            )
            next_status = (
                NotificationStatus.DELIVERED_SIMULATED
                if outcome == DeliveryOutcome.DELIVERED_SIMULATED
                else NotificationStatus.FAILED
            )
            prior_status = notification.status
            notification.status = next_status
            notification.save(update_fields=["status"])
            record_successful_action(
                actor=actor,
                action=action,
                resource_type="NOTIFICATION",
                resource_id=notification.pk,
                safe_context={
                    **expected_context,
                    "from_status": prior_status,
                    "attempt_number": attempt_number,
                },
            )
            return CommandResult(attempt)
    except (
        AuthorizationDenied,
        PolicyNotConfigured,
        InvalidStateTransition,
        IdempotencyConflict,
    ):
        _audit_denied(actor, notification_id, operation)
        raise
    except IntegrityError as exc:
        _audit_denied(actor, notification_id, f"{operation}.conflict")
        raise ResourceConflict(
            "Notification delivery command conflicts with an existing attempt."
        ) from exc


def record_simulated_delivery(
    *,
    notification_id: UUID,
    actor: Actor,
    command_id: UUID,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[NotificationDeliveryAttempt]:
    return _record_delivery_outcome(
        notification_id=notification_id,
        actor=actor,
        command_id=command_id,
        outcome=DeliveryOutcome.DELIVERED_SIMULATED,
        failure_code=None,
        policy=policy,
    )


def record_delivery_failure(
    *,
    notification_id: UUID,
    actor: Actor,
    command_id: UUID,
    safe_failure_code: str,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[NotificationDeliveryAttempt]:
    return _record_delivery_outcome(
        notification_id=notification_id,
        actor=actor,
        command_id=command_id,
        outcome=DeliveryOutcome.FAILED,
        failure_code=safe_failure_code,
        policy=policy,
    )


def mark_notification_read(
    *, notification_id: UUID, actor: Actor, command_id: UUID
) -> CommandResult[Notification]:
    try:
        user = require_human(actor)
        with transaction.atomic():
            notification = _locked_notification(notification_id)
            prior = _audit_command(command_id)
            context = {"command_id": str(command_id), "to_status": NotificationStatus.READ}
            if prior:
                _assert_command_intent(
                    prior=prior,
                    notification=notification,
                    actor_id=user.pk,
                    action="NOTIFICATION_READ",
                    expected_context=context,
                )
                return CommandResult(notification, replayed=True)
            if notification.recipient_user_id != user.pk:
                raise AuthorizationDenied("Only the notification recipient may mark it read.")
            if notification.status == NotificationStatus.READ:
                record_successful_action(
                    actor=actor,
                    action="NOTIFICATION_READ",
                    resource_type="NOTIFICATION",
                    resource_id=notification.pk,
                    safe_context=context,
                )
                return CommandResult(notification)
            if notification.status != NotificationStatus.DELIVERED_SIMULATED:
                raise InvalidStateTransition("Only simulated-delivered notifications can be read.")
            notification.status = NotificationStatus.READ
            notification.read_at = timezone.now()
            notification.save(update_fields=["status", "read_at"])
            record_successful_action(
                actor=actor,
                action="NOTIFICATION_READ",
                resource_type="NOTIFICATION",
                resource_id=notification.pk,
                safe_context={
                    "command_id": command_id,
                    "from_status": NotificationStatus.DELIVERED_SIMULATED,
                    "to_status": NotificationStatus.READ,
                },
            )
            return CommandResult(notification)
    except AuthorizationDenied, InvalidStateTransition, IdempotencyConflict:
        _audit_denied(actor, notification_id, "notification.read")
        raise


def cancel_notification(
    *,
    notification_id: UUID,
    actor: Actor,
    command_id: UUID,
    policy: AuthorizationPolicy | None = None,
) -> CommandResult[Notification]:
    try:
        user = require_human(actor)
        with transaction.atomic():
            notification = _locked_notification(notification_id)
            require_authorized(policy, "notification.cancel", actor, notification)
            prior = _audit_command(command_id)
            context = {"command_id": str(command_id), "to_status": NotificationStatus.CANCELLED}
            if prior:
                _assert_command_intent(
                    prior=prior,
                    notification=notification,
                    actor_id=user.pk,
                    action="NOTIFICATION_CANCELLED",
                    expected_context=context,
                )
                return CommandResult(notification, replayed=True)
            if notification.status == NotificationStatus.CANCELLED:
                record_successful_action(
                    actor=actor,
                    action="NOTIFICATION_CANCELLED",
                    resource_type="NOTIFICATION",
                    resource_id=notification.pk,
                    safe_context=context,
                )
                return CommandResult(notification)
            if notification.status in {
                NotificationStatus.DELIVERED_SIMULATED,
                NotificationStatus.READ,
            }:
                raise InvalidStateTransition(
                    "A delivered or read notification cannot be cancelled."
                )
            prior_status = notification.status
            notification.status = NotificationStatus.CANCELLED
            notification.save(update_fields=["status"])
            record_successful_action(
                actor=actor,
                action="NOTIFICATION_CANCELLED",
                resource_type="NOTIFICATION",
                resource_id=notification.pk,
                safe_context={
                    "command_id": command_id,
                    "from_status": prior_status,
                    "to_status": NotificationStatus.CANCELLED,
                },
            )
            return CommandResult(notification)
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition, IdempotencyConflict:
        _audit_denied(actor, notification_id, "notification.cancel")
        raise
