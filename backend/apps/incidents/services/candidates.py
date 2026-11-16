"""Explicit candidate association and human review operations."""

from uuid import UUID

from django.db import IntegrityError, transaction

from apps.audit.models import AuditEvent
from apps.audit.services import record_denied_action, record_successful_action
from apps.detection.models import DetectionEvent
from apps.incidents.models import (
    AccidentCandidate,
    AccidentIncident,
    AssociationMethod,
    CandidateDetectionEvent,
    CandidateReview,
    CandidateStatus,
    IncidentStatus,
    IncidentStatusHistory,
    ReviewDecision,
)
from apps.sources.models import VideoSourceAuthorizationStatus
from common.domain.actors import Actor, MachineActor
from common.domain.authorization import require_ai_service, require_human, require_known_actor
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


def _audit_denied(actor: Actor, resource_id: UUID | None, reason: str) -> None:
    record_denied_action(
        actor=actor,
        action="DOMAIN_ACTION_DENIED",
        resource_type="CANDIDATE",
        resource_id=resource_id,
        safe_context={"reason_code": reason},
    )


def create_candidate(
    *,
    detection_event_id: UUID,
    actor: Actor,
    policy: AuthorizationPolicy | None = None,
) -> AccidentCandidate:
    """Create one candidate from an explicitly selected event, without matching heuristics."""

    try:
        user = None
        if isinstance(actor, MachineActor):
            require_ai_service(actor)
        else:
            user = require_human(actor)
        with transaction.atomic():
            event = (
                DetectionEvent.objects.select_related("video_source")
                .select_for_update()
                .filter(pk=detection_event_id)
                .first()
            )
            if event is None:
                raise ResourceNotFound("Detection event was not found.")
            if event.video_source.authorization_status != VideoSourceAuthorizationStatus.AUTHORIZED:
                raise AuthorizationDenied("The event source is no longer authorized.")
            if not isinstance(actor, MachineActor):
                require_authorized(policy, "candidate.create", actor, event)
            existing_link = (
                CandidateDetectionEvent.objects.select_related("candidate")
                .filter(detection_event=event)
                .first()
            )
            if existing_link is not None:
                return existing_link.candidate
            candidate = AccidentCandidate.objects.create(status=CandidateStatus.RECEIVED)
            CandidateDetectionEvent.objects.create(
                candidate=candidate,
                detection_event=event,
                association_method="RULE_BASED" if isinstance(actor, MachineActor) else "MANUAL",
                linked_by_user=user,
            )
            record_successful_action(
                actor=actor,
                action="CANDIDATE_CREATED",
                resource_type="CANDIDATE",
                resource_id=candidate.pk,
                safe_context={"event_id": event.pk, "source_id": event.video_source_id},
            )
            return candidate
    except (
        AuthorizationDenied,
        PolicyNotConfigured,
        InvalidStateTransition,
        IdempotencyConflict,
        ResourceConflict,
    ):
        _audit_denied(actor, None, "candidate.create")
        raise
    except IntegrityError as exc:
        _audit_denied(actor, None, "candidate.create.conflict")
        raise ResourceConflict("The event is already associated with another candidate.") from exc


def associate_detection_event(
    *,
    candidate_id: UUID,
    detection_event_id: UUID,
    actor: Actor,
    association_method: str = AssociationMethod.MANUAL,
    policy: AuthorizationPolicy | None = None,
) -> CandidateDetectionEvent:
    try:
        user = require_human(actor)
        if association_method not in {
            AssociationMethod.MANUAL,
            AssociationMethod.REVIEWER_CONFIRMED,
        }:
            raise BusinessRuleViolation(
                "Human event association must be manual or reviewer-confirmed."
            )
        with transaction.atomic():
            candidate = (
                AccidentCandidate.objects.select_for_update().filter(pk=candidate_id).first()
            )
            if candidate is None:
                raise ResourceNotFound("Candidate was not found.")
            require_authorized(policy, "candidate.associate", actor, candidate)
            if candidate.status not in {CandidateStatus.RECEIVED, CandidateStatus.UNDER_REVIEW}:
                raise InvalidStateTransition("Events cannot be added to a final candidate.")
            event = (
                DetectionEvent.objects.select_related("video_source")
                .filter(pk=detection_event_id)
                .first()
            )
            if event is None:
                raise ResourceNotFound("Detection event was not found.")
            if event.video_source.authorization_status != VideoSourceAuthorizationStatus.AUTHORIZED:
                raise AuthorizationDenied("The event source is no longer authorized.")
            prior = (
                CandidateDetectionEvent.objects.select_related("candidate")
                .filter(detection_event=event)
                .first()
            )
            if prior:
                if prior.candidate_id == candidate.pk:
                    if (
                        prior.association_method != association_method
                        or prior.linked_by_user_id != user.pk
                    ):
                        raise ResourceConflict(
                            "The event already has a different association record."
                        )
                    return prior
                raise ResourceConflict("A detection event can belong to only one candidate.")
            link = CandidateDetectionEvent.objects.create(
                candidate=candidate,
                detection_event=event,
                association_method=association_method,
                linked_by_user=user,
            )
            record_successful_action(
                actor=actor,
                action="CANDIDATE_EVENT_ASSOCIATED",
                resource_type="CANDIDATE",
                resource_id=candidate.pk,
                safe_context={"event_id": event.pk, "association_method": association_method},
            )
            return link
    except (
        AuthorizationDenied,
        PolicyNotConfigured,
        InvalidStateTransition,
        IdempotencyConflict,
        ResourceConflict,
        BusinessRuleViolation,
    ):
        _audit_denied(actor, candidate_id, "candidate.associate")
        raise
    except IntegrityError as exc:
        _audit_denied(actor, candidate_id, "candidate.associate.conflict")
        raise ResourceConflict("The event is already associated with a candidate.") from exc


def get_candidate(
    candidate_id: UUID, *, actor: Actor, policy: AuthorizationPolicy | None = None
) -> AccidentCandidate:
    require_known_actor(actor)
    candidate = AccidentCandidate.objects.filter(pk=candidate_id).first()
    if candidate is None:
        raise ResourceNotFound("Candidate was not found.")
    require_authorized(policy, "candidate.read", actor, candidate)
    return candidate


def list_reviewable_candidates(*, actor: Actor, policy: AuthorizationPolicy | None = None):
    require_human(actor)
    require_authorized(policy, "candidate.read_queue", actor)
    return (
        AccidentCandidate.objects.filter(
            status__in=[CandidateStatus.RECEIVED, CandidateStatus.UNDER_REVIEW],
            detection_links__isnull=False,
        )
        .distinct()
        .order_by("created_at")
    )


def begin_candidate_review(
    *, candidate_id: UUID, actor: Actor, command_id: UUID, policy: AuthorizationPolicy | None = None
) -> CommandResult[AccidentCandidate]:
    try:
        require_human(actor)
        with transaction.atomic():
            candidate = (
                AccidentCandidate.objects.select_for_update().filter(pk=candidate_id).first()
            )
            if candidate is None:
                raise ResourceNotFound("Candidate was not found.")
            require_authorized(policy, "candidate.review", actor, candidate)
            prior_audit = AuditEvent.objects.filter(
                safe_context__command_id=str(command_id)
            ).first()
            if prior_audit:
                if (
                    prior_audit.resource_type != AuditEvent.ResourceType.CANDIDATE
                    or prior_audit.resource_id != candidate.pk
                    or prior_audit.action != "CANDIDATE_REVIEW_STARTED"
                    or prior_audit.actor_user_id != actor.user_id
                ):
                    raise IdempotencyConflict("Review command identifier has different intent.")
                return CommandResult(candidate, replayed=True)
            if candidate.status == CandidateStatus.UNDER_REVIEW:
                raise ResourceConflict("Candidate is already under review.")
            if candidate.status != CandidateStatus.RECEIVED:
                raise InvalidStateTransition("Only received candidates can enter review.")
            if not candidate.detection_links.exists():
                raise InvalidStateTransition("A candidate needs event provenance before review.")
            candidate.status = CandidateStatus.UNDER_REVIEW
            candidate.save(update_fields=["status", "updated_at"])
            record_successful_action(
                actor=actor,
                action="CANDIDATE_REVIEW_STARTED",
                resource_type="CANDIDATE",
                resource_id=candidate.pk,
                safe_context={"command_id": command_id, "to_status": candidate.status},
            )
            return CommandResult(candidate)
    except (
        AuthorizationDenied,
        PolicyNotConfigured,
        InvalidStateTransition,
        IdempotencyConflict,
        ResourceConflict,
    ):
        _audit_denied(actor, candidate_id, "candidate.review")
        raise


def _review_candidate(
    *,
    candidate_id: UUID,
    actor: Actor,
    command_id: UUID,
    decision: str,
    rationale: str | None,
    policy: AuthorizationPolicy | None,
) -> CommandResult[AccidentIncident | AccidentCandidate]:
    operation = "candidate.verify" if decision == ReviewDecision.VERIFIED else "candidate.reject"
    try:
        reviewer = require_human(actor)
        normalized_rationale = rationale.strip() if rationale and rationale.strip() else None
        if decision == ReviewDecision.REJECTED and normalized_rationale is None:
            raise InvalidStateTransition("A rejection rationale is required.")
        with transaction.atomic():
            candidate = (
                AccidentCandidate.objects.select_for_update().filter(pk=candidate_id).first()
            )
            if candidate is None:
                raise ResourceNotFound("Candidate was not found.")
            require_authorized(policy, operation, actor, candidate)
            prior_command = CandidateReview.objects.filter(command_id=command_id).first()
            if prior_command:
                if (
                    prior_command.candidate_id != candidate.pk
                    or prior_command.reviewer_id != reviewer.pk
                    or prior_command.decision != decision
                    or prior_command.rationale != normalized_rationale
                ):
                    raise IdempotencyConflict("Review command identifier has different intent.")
                if decision == ReviewDecision.VERIFIED:
                    return CommandResult(
                        AccidentIncident.objects.get(candidate=candidate), replayed=True
                    )
                return CommandResult(candidate, replayed=True)
            if candidate.status != CandidateStatus.UNDER_REVIEW:
                raise InvalidStateTransition(
                    "Only candidates under review can receive a final decision."
                )
            if not candidate.detection_links.exists():
                raise InvalidStateTransition("A candidate needs event provenance before review.")
            CandidateReview.objects.create(
                candidate=candidate,
                reviewer=reviewer,
                decision=decision,
                rationale=normalized_rationale,
                command_id=command_id,
            )
            candidate.status = (
                CandidateStatus.VERIFIED
                if decision == ReviewDecision.VERIFIED
                else CandidateStatus.REJECTED
            )
            candidate.save(update_fields=["status", "updated_at"])
            if decision == ReviewDecision.VERIFIED:
                incident = AccidentIncident.objects.create(
                    candidate=candidate,
                    status=IncidentStatus.OPEN,
                )
                IncidentStatusHistory.objects.create(
                    incident=incident,
                    from_status=None,
                    to_status=IncidentStatus.OPEN,
                    changed_by_user=reviewer,
                    command_id=command_id,
                )
                record_successful_action(
                    actor=actor,
                    action="CANDIDATE_VERIFIED",
                    resource_type="CANDIDATE",
                    resource_id=candidate.pk,
                    safe_context={"command_id": command_id, "incident_id": incident.pk},
                )
                return CommandResult(incident)
            record_successful_action(
                actor=actor,
                action="CANDIDATE_REJECTED",
                resource_type="CANDIDATE",
                resource_id=candidate.pk,
                safe_context={"command_id": command_id},
            )
            return CommandResult(candidate)
    except (
        AuthorizationDenied,
        PolicyNotConfigured,
        InvalidStateTransition,
        IdempotencyConflict,
        ResourceConflict,
    ):
        _audit_denied(actor, candidate_id, operation)
        raise
    except IntegrityError as exc:
        _audit_denied(actor, candidate_id, f"{operation}.conflict")
        raise ResourceConflict("Candidate decision conflicts with an existing review.") from exc


def verify_candidate(
    *, candidate_id: UUID, actor: Actor, command_id: UUID, rationale: str = "", policy=None
) -> CommandResult[AccidentIncident]:
    result = _review_candidate(
        candidate_id=candidate_id,
        actor=actor,
        command_id=command_id,
        decision=ReviewDecision.VERIFIED,
        rationale=rationale or None,
        policy=policy,
    )
    return result  # type: ignore[return-value]


def reject_candidate(
    *, candidate_id: UUID, actor: Actor, command_id: UUID, rationale: str, policy=None
) -> CommandResult[AccidentCandidate]:
    result = _review_candidate(
        candidate_id=candidate_id,
        actor=actor,
        command_id=command_id,
        decision=ReviewDecision.REJECTED,
        rationale=rationale,
        policy=policy,
    )
    return result  # type: ignore[return-value]
