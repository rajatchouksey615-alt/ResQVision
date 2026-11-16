"""Reusable identity and organization-scope checks for domain services."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser

from apps.organizations.models import MembershipStatus, Organization, OrganizationMembership
from common.domain.actors import Actor, HumanActor, MachineActor
from common.domain.exceptions import AuthorizationDenied

AI_SERVICE_REF = "AI_SERVICE"


def require_human(actor: Actor) -> AbstractBaseUser:
    if not isinstance(actor, HumanActor) or not actor.user.pk:
        raise AuthorizationDenied("An active human account is required.")
    user = get_user_model().objects.filter(pk=actor.user.pk, is_active=True).first()
    if user is None:
        raise AuthorizationDenied("An active human account is required.")
    return user


def require_ai_service(actor: Actor) -> MachineActor:
    if not isinstance(actor, MachineActor) or actor.service_ref != AI_SERVICE_REF:
        raise AuthorizationDenied("An authenticated AI_SERVICE actor is required.")
    return actor


def require_known_actor(actor: Actor) -> AbstractBaseUser | MachineActor:
    """Validate an actor against the identities currently supported by this backend."""

    if isinstance(actor, HumanActor):
        return require_human(actor)
    return require_ai_service(actor)


def require_membership(
    actor: Actor,
    organization: Organization,
    *,
    expected_role: str | None = None,
) -> OrganizationMembership:
    user = require_human(actor)
    if not organization.is_active:
        raise AuthorizationDenied("The target organization is inactive.")
    membership = (
        OrganizationMembership.objects.select_related("organization", "role_group")
        .filter(
            user=user,
            organization=organization,
            status=MembershipStatus.ACTIVE,
        )
        .first()
    )
    if membership is None:
        raise AuthorizationDenied("An active membership for this organization is required.")
    group_name = membership.role_group.name
    if group_name != organization.organization_kind:
        raise AuthorizationDenied("Membership role does not match the organization kind.")
    if expected_role is not None and group_name != expected_role:
        raise AuthorizationDenied("The membership does not match the assignment target.")
    return membership
