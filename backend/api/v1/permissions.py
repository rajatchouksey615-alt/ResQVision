"""Reusable human, machine, group, membership, and object permission checks."""

from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

from apps.notifications.models import Notification
from apps.responses.models import ResponseAssignment
from common.domain.actors import HumanActor, MachineActor
from common.domain.authorization import require_membership
from common.domain.exceptions import AuthorizationDenied

from .selectors import active_memberships_for, visible_assignment_queryset


class IsAuthenticatedHuman(BasePermission):
    def has_permission(self, request, view):
        del view
        user_model = get_user_model()
        return (
            isinstance(getattr(request, "user", None), user_model)
            and request.user.is_authenticated
            and request.user.is_active
        )


class IsAuthenticatedMachine(BasePermission):
    def has_permission(self, request, view):
        del view
        return isinstance(getattr(request, "user", None), MachineActor)


class IsActiveAccount(IsAuthenticatedHuman):
    """Explicit alias for views whose user must be active at request time."""


class HasApprovedGroupRole(BasePermission):
    """Require a current Django Group; superuser/staff flags do not bypass it."""

    def has_permission(self, request, view):
        required = getattr(view, "required_group_roles", ())
        return bool(
            required
            and IsAuthenticatedHuman().has_permission(request, view)
            and request.user.groups.filter(name__in=required).exists()
        )


class HasActiveOrganizationMembership(BasePermission):
    def has_permission(self, request, view):
        organization_id = view.kwargs.get("organization_id")
        return bool(
            organization_id
            and IsAuthenticatedHuman().has_permission(request, view)
            and active_memberships_for(request.user)
            .filter(organization_id=organization_id)
            .exists()
        )


class HasAssignmentTargetAccess(BasePermission):
    def has_object_permission(self, request, view, obj):
        del view
        if not isinstance(obj, ResponseAssignment):
            return False
        try:
            require_membership(
                HumanActor(request.user),
                obj.target_organization,
                expected_role=obj.target_organization.organization_kind,
            )
        except AuthorizationDenied, AttributeError:
            return False
        return True


class HasNotificationOwnership(BasePermission):
    def has_object_permission(self, request, view, obj):
        del view
        return isinstance(obj, Notification) and obj.recipient_user_id == request.user.pk


class HasCandidateReviewPermission(BasePermission):
    """Candidate review routes remain policy-blocked until reviewer authority is approved."""

    def has_permission(self, request, view):
        del request, view
        return False


class HasIncidentObjectAccess(BasePermission):
    def has_object_permission(self, request, view, obj):
        del view
        from apps.incidents.models import AccidentIncident

        if not isinstance(obj, AccidentIncident):
            return False
        return visible_assignment_queryset(request.user).filter(incident_id=obj.pk).exists()


class HasEvidenceObjectAccess(BasePermission):
    """Evidence object policy remains unavailable until field-level scope is approved."""

    def has_object_permission(self, request, view, obj):
        del request, view, obj
        return False
