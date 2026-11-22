"""Organization-scoped Police reviewer assignment commands."""

from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.audit.models import AuditEvent
from apps.audit.services import record_denied_action, record_successful_action
from apps.incidents.models import (
    AccidentCandidate,
    CandidateReviewerAssignment,
    CandidateStatus,
)
from apps.organizations.models import (
    MembershipStatus,
    Organization,
    OrganizationKind,
    OrganizationMembership,
)
from common.domain.actors import Actor
from common.domain.authorization import require_human
from common.domain.exceptions import (
    AuthorizationDenied,
    BusinessRuleViolation,
    IdempotencyConflict,
    InvalidStateTransition,
    ResourceConflict,
    ResourceNotFound,
)
from common.domain.results import CommandResult


def _audit_denied(actor: Actor, candidate_id: UUID, reason: str) -> None:
    record_denied_action(
        actor=actor,
        action="DOMAIN_ACTION_DENIED",
        resource_type=AuditEvent.ResourceType.CANDIDATE,
        resource_id=candidate_id,
        safe_context={"reason_code": reason},
    )


def _active_police_membership(*, user, organization: Organization, lock: bool):
    memberships = OrganizationMembership.objects
    if lock:
        memberships = memberships.select_for_update(of=("self",))
    return memberships.filter(
        user=user,
        organization=organization,
        status=MembershipStatus.ACTIVE,
        organization__is_active=True,
        organization__organization_kind=OrganizationKind.POLICE,
        role_group__name=OrganizationKind.POLICE,
    ).first()


def _same_assignment_intent(
    assignment: CandidateReviewerAssignment,
    *,
    candidate_id: UUID,
    reviewer_id: UUID,
    assigner_id: UUID,
    organization_id: UUID,
) -> bool:
    return (
        assignment.candidate_id == candidate_id
        and assignment.reviewer_id == reviewer_id
        and assignment.assigned_by_user_id == assigner_id
        and assignment.police_organization_id == organization_id
    )


def assign_candidate_reviewer(
    *,
    candidate_id: UUID,
    reviewer_id: UUID,
    actor: Actor,
    command_id: UUID,
) -> CommandResult[CandidateReviewerAssignment]:
    """Assign one active, same-organization Police reviewer to a received candidate."""

    try:
        with transaction.atomic():
            actor_user = require_human(actor)
            assigner = (
                get_user_model()
                .objects.select_for_update()
                .filter(pk=actor_user.pk, is_active=True)
                .first()
            )
            if assigner is None or not assigner.groups.filter(name="ADMIN").exists():
                raise AuthorizationDenied("An active ADMIN-group assigner is required.")

            candidate = (
                AccidentCandidate.objects.select_for_update().filter(pk=candidate_id).first()
            )
            if candidate is None:
                raise ResourceNotFound("Candidate was not found.")
            if candidate.police_organization_id is None:
                raise BusinessRuleViolation("Candidate has no valid Police organization.")

            organization = (
                Organization.objects.select_for_update()
                .filter(
                    pk=candidate.police_organization_id,
                    organization_kind=OrganizationKind.POLICE,
                    is_active=True,
                )
                .first()
            )
            if organization is None:
                raise BusinessRuleViolation("Candidate has no valid Police organization.")
            if (
                _active_police_membership(user=assigner, organization=organization, lock=True)
                is None
            ):
                raise AuthorizationDenied(
                    "An active Police membership in the candidate organization is required."
                )

            reviewer = (
                get_user_model()
                .objects.select_for_update()
                .filter(pk=reviewer_id, is_active=True)
                .first()
            )
            if (
                reviewer is None
                or _active_police_membership(user=reviewer, organization=organization, lock=True)
                is None
            ):
                raise AuthorizationDenied(
                    "The reviewer must be active and belong to the candidate Police organization."
                )

            prior_command = CandidateReviewerAssignment.objects.filter(
                command_id=command_id
            ).first()
            if prior_command is not None:
                if not _same_assignment_intent(
                    prior_command,
                    candidate_id=candidate.pk,
                    reviewer_id=reviewer.pk,
                    assigner_id=assigner.pk,
                    organization_id=organization.pk,
                ):
                    raise IdempotencyConflict("Assignment command identifier has different intent.")
                return CommandResult(prior_command, replayed=True)

            if candidate.status != CandidateStatus.RECEIVED:
                raise InvalidStateTransition("Only received candidates can be assigned.")

            if CandidateReviewerAssignment.objects.filter(candidate=candidate).exists():
                raise ResourceConflict("Candidate already has a reviewer assignment.")

            assignment = CandidateReviewerAssignment.objects.create(
                candidate=candidate,
                police_organization=organization,
                reviewer=reviewer,
                assigned_by_user=assigner,
                command_id=command_id,
            )
            record_successful_action(
                actor=actor,
                action="CANDIDATE_REVIEWER_ASSIGNED",
                resource_type=AuditEvent.ResourceType.CANDIDATE,
                resource_id=candidate.pk,
                safe_context={
                    "assignment_id": assignment.pk,
                    "candidate_id": candidate.pk,
                    "organization_id": organization.pk,
                    "reviewer_id": reviewer.pk,
                    "command_id": command_id,
                },
            )
            return CommandResult(assignment)
    except (
        AuthorizationDenied,
        BusinessRuleViolation,
        IdempotencyConflict,
        InvalidStateTransition,
        ResourceConflict,
        ResourceNotFound,
    ) as exc:
        reason = {
            AuthorizationDenied: "candidate.assignment.unauthorized",
            BusinessRuleViolation: "candidate.assignment.invalid_organization",
            IdempotencyConflict: "candidate.assignment.idempotency_conflict",
            InvalidStateTransition: "candidate.assignment.invalid_state",
            ResourceConflict: "candidate.assignment.conflict",
            ResourceNotFound: "candidate.assignment.not_found",
        }[type(exc)]
        _audit_denied(actor, candidate_id, reason)
        raise
    except IntegrityError as exc:
        prior_command = CandidateReviewerAssignment.objects.filter(command_id=command_id).first()
        if prior_command is not None:
            candidate = (
                AccidentCandidate.objects.filter(pk=candidate_id)
                .only("police_organization_id")
                .first()
            )
            if candidate is not None and _same_assignment_intent(
                prior_command,
                candidate_id=candidate_id,
                reviewer_id=reviewer_id,
                assigner_id=getattr(actor, "user_id", None),
                organization_id=candidate.police_organization_id,
            ):
                return CommandResult(prior_command, replayed=True)
            _audit_denied(actor, candidate_id, "candidate.assignment.idempotency_conflict")
            raise IdempotencyConflict(
                "Assignment command identifier has different intent."
            ) from exc

        existing = CandidateReviewerAssignment.objects.filter(candidate_id=candidate_id).first()
        if existing is not None:
            _audit_denied(actor, candidate_id, "candidate.assignment.conflict")
            raise ResourceConflict("Candidate already has a reviewer assignment.") from exc

        _audit_denied(actor, candidate_id, "candidate.assignment.conflict")
        raise ResourceConflict("The assignment conflicts with existing data.") from exc
