"""Scoped membership checks and policy-gated membership changes."""

from uuid import UUID

from django.db import transaction

from apps.audit.models import AuditEvent
from apps.audit.services import record_denied_action, record_successful_action
from apps.organizations.models import MembershipStatus, Organization, OrganizationMembership
from common.domain.actors import Actor
from common.domain.authorization import require_human, require_membership
from common.domain.exceptions import (
    AuthorizationDenied,
    IdempotencyConflict,
    PolicyNotConfigured,
    ResourceNotFound,
)
from common.domain.policies import AuthorizationPolicy, require_authorized


def validate_organization_membership(
    *, actor: Actor, organization_id: UUID, expected_role: str | None = None
) -> OrganizationMembership:
    require_human(actor)
    organization = Organization.objects.filter(pk=organization_id).first()
    if organization is None:
        raise ResourceNotFound("Organization was not found.")
    return require_membership(actor, organization, expected_role=expected_role)


def _change_membership(
    *,
    membership_id: UUID,
    actor: Actor,
    command_id: UUID,
    status: str,
    policy: AuthorizationPolicy | None,
) -> OrganizationMembership:
    operation = f"membership.{status.lower()}"
    action = {
        MembershipStatus.ACTIVE: "MEMBERSHIP_ACTIVATED",
        MembershipStatus.SUSPENDED: "MEMBERSHIP_SUSPENDED",
        MembershipStatus.REVOKED: "MEMBERSHIP_REVOKED",
    }[status]
    try:
        user = require_human(actor)
        with transaction.atomic():
            membership = (
                OrganizationMembership.objects.select_for_update()
                .select_related("organization", "role_group")
                .filter(pk=membership_id)
                .first()
            )
            if membership is None:
                raise ResourceNotFound("Membership was not found.")
            require_authorized(policy, operation, actor, membership)
            prior = AuditEvent.objects.filter(safe_context__command_id=str(command_id)).first()
            if prior:
                if (
                    prior.resource_type != AuditEvent.ResourceType.MEMBERSHIP
                    or prior.resource_id != membership.pk
                    or prior.action != action
                    or prior.actor_user_id != user.pk
                ):
                    raise IdempotencyConflict("Membership command identifier has different intent.")
                return membership
            if membership.role_group.name != membership.organization.organization_kind:
                raise AuthorizationDenied("Membership role does not match organization kind.")
            if not membership.organization.is_active and status == MembershipStatus.ACTIVE:
                raise AuthorizationDenied("An inactive organization cannot receive active members.")
            if membership.status == MembershipStatus.REVOKED and status != MembershipStatus.REVOKED:
                raise AuthorizationDenied("A revoked membership cannot be reactivated.")
            membership.status = status
            membership.full_clean()
            membership.save(update_fields=["status", "updated_at"])
            record_successful_action(
                actor=actor,
                action=action,
                resource_type="MEMBERSHIP",
                resource_id=membership.pk,
                safe_context={
                    "command_id": command_id,
                    "organization_id": membership.organization_id,
                },
            )
            return membership
    except AuthorizationDenied, PolicyNotConfigured, IdempotencyConflict:
        record_denied_action(
            actor=actor,
            action="DOMAIN_ACTION_DENIED",
            resource_type="MEMBERSHIP",
            resource_id=membership_id,
            safe_context={"reason_code": operation},
        )
        raise


def activate_membership(*, membership_id: UUID, actor: Actor, command_id: UUID, policy=None):
    return _change_membership(
        membership_id=membership_id,
        actor=actor,
        command_id=command_id,
        status=MembershipStatus.ACTIVE,
        policy=policy,
    )


def suspend_membership(*, membership_id: UUID, actor: Actor, command_id: UUID, policy=None):
    return _change_membership(
        membership_id=membership_id,
        actor=actor,
        command_id=command_id,
        status=MembershipStatus.SUSPENDED,
        policy=policy,
    )


def revoke_membership(*, membership_id: UUID, actor: Actor, command_id: UUID, policy=None):
    return _change_membership(
        membership_id=membership_id,
        actor=actor,
        command_id=command_id,
        status=MembershipStatus.REVOKED,
        policy=policy,
    )
