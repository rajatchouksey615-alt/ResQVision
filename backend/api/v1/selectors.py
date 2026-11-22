"""Authorization-scoped read querysets; filtering always precedes pagination."""

from django.db.models import F

from apps.incidents.models import AccidentCandidate, AccidentIncident
from apps.notifications.models import Notification
from apps.organizations.models import MembershipStatus, OrganizationMembership
from apps.responses.models import AssignmentStatus, ResponseAssignment


def visible_candidate_queryset(user):
    """Candidates assigned to this active Police member in the bound organization."""

    return (
        AccidentCandidate.objects.filter(
            police_organization_id=F("reviewer_assignment__police_organization_id"),
            reviewer_assignment__reviewer=user,
            reviewer_assignment__reviewer__is_active=True,
            reviewer_assignment__police_organization__is_active=True,
            reviewer_assignment__police_organization__organization_kind="POLICE",
            reviewer_assignment__police_organization__memberships__user=user,
            reviewer_assignment__police_organization__memberships__status=MembershipStatus.ACTIVE,
            reviewer_assignment__police_organization__memberships__role_group__name="POLICE",
        )
        .select_related("police_organization", "reviewer_assignment")
        .distinct()
        .order_by("-created_at", "pk")
    )


def active_memberships_for(user):
    return (
        OrganizationMembership.objects.filter(
            user=user,
            status=MembershipStatus.ACTIVE,
            organization__is_active=True,
            role_group__name=F("organization__organization_kind"),
        )
        .select_related("organization", "role_group")
        .order_by("organization__display_name", "pk")
    )


def visible_assignment_queryset(user):
    """Assignments in the user's active organization; replaced targets are hidden."""

    visible_statuses = [
        AssignmentStatus.PENDING,
        AssignmentStatus.ACKNOWLEDGED,
        AssignmentStatus.IN_PROGRESS,
        AssignmentStatus.COMPLETED,
        AssignmentStatus.UNABLE_TO_RESPOND,
    ]
    return (
        ResponseAssignment.objects.filter(
            target_organization__is_active=True,
            target_organization__memberships__user=user,
            target_organization__memberships__status=MembershipStatus.ACTIVE,
            target_organization__memberships__role_group__name=F(
                "target_organization__organization_kind"
            ),
            status__in=visible_statuses,
        )
        .select_related("incident", "target_organization")
        .distinct()
        .order_by("-created_at", "pk")
    )


def visible_incident_queryset(user):
    return (
        AccidentIncident.objects.filter(response_assignments__in=visible_assignment_queryset(user))
        .distinct()
        .order_by("-created_at", "pk")
    )


def visible_notifications_queryset(user):
    return Notification.objects.filter(recipient_user=user).order_by("-created_at", "pk")
