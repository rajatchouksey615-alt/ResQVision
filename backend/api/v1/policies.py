"""Narrow API adapters for read rules already described by the role matrix."""

from django.contrib.auth import get_user_model

from apps.organizations.models import (
    MembershipStatus,
    Organization,
    OrganizationKind,
    OrganizationMembership,
)
from common.domain.actors import HumanActor
from common.domain.exceptions import PolicyNotConfigured

from .selectors import visible_assignment_queryset, visible_candidate_queryset


class AssignedIncidentReadPolicy:
    """Permit only the assigned organization scope for incident summaries."""

    def authorize(self, operation, actor, resource=None) -> bool:
        if operation != "incident.read":
            raise PolicyNotConfigured(f"No approved policy is configured for {operation}.")
        if (
            not isinstance(actor, HumanActor)
            or resource is None
            or not getattr(resource, "pk", None)
        ):
            return False
        return visible_assignment_queryset(actor.user).filter(incident_id=resource.pk).exists()


class AssignedCandidateReviewPolicy:
    """Permit review commands only for the caller's active Police assignment."""

    _OPERATIONS = frozenset({"candidate.review", "candidate.verify", "candidate.reject"})

    def authorize(self, operation, actor, resource=None) -> bool:
        if operation not in self._OPERATIONS:
            raise PolicyNotConfigured(f"No approved policy is configured for {operation}.")
        if (
            not isinstance(actor, HumanActor)
            or resource is None
            or not getattr(resource, "pk", None)
        ):
            return False
        if not visible_candidate_queryset(actor.user).filter(pk=resource.pk).exists():
            return False
        organization = (
            Organization.objects.select_for_update()
            .filter(
                pk=resource.police_organization_id,
                organization_kind=OrganizationKind.POLICE,
                is_active=True,
            )
            .first()
        )
        if organization is None:
            return False
        return (
            OrganizationMembership.objects.select_for_update(of=("self",))
            .filter(
                user_id=actor.user_id,
                organization=organization,
                status=MembershipStatus.ACTIVE,
                role_group__name=OrganizationKind.POLICE,
            )
            .exists()
            and get_user_model().objects.filter(pk=actor.user_id, is_active=True).exists()
        )
