"""Narrow API adapters for read rules already described by the role matrix."""

from common.domain.actors import HumanActor
from common.domain.exceptions import PolicyNotConfigured

from .selectors import visible_assignment_queryset


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
