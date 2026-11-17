"""Throttle classes for identities that are not Django user models."""

from rest_framework.throttling import ScopedRateThrottle

from common.domain.actors import MachineActor


class MachineScopedRateThrottle(ScopedRateThrottle):
    """Rate-limit a verified machine principal by service identity."""

    def get_cache_key(self, request, view):
        actor = request.user
        if isinstance(actor, MachineActor):
            return self.cache_format % {
                "scope": self.scope,
                "ident": actor.service_ref,
            }
        return super().get_cache_key(request, view)
