"""Explicit authorization hooks; unresolved authority fails closed."""

from dataclasses import dataclass
from typing import Protocol

from common.domain.actors import Actor
from common.domain.exceptions import AuthorizationDenied, PolicyNotConfigured


class AuthorizationPolicy(Protocol):
    def authorize(self, operation: str, actor: Actor, resource: object | None = None) -> bool:
        """Return whether the actor may perform the named operation."""


@dataclass(frozen=True, slots=True)
class DenyByDefaultPolicy:
    """Production-safe policy for operations pending explicit project approval."""

    def authorize(self, operation: str, actor: Actor, resource: object | None = None) -> bool:
        raise PolicyNotConfigured(f"No approved policy is configured for {operation}.")


DEFAULT_POLICY = DenyByDefaultPolicy()


def require_authorized(
    policy: AuthorizationPolicy | None,
    operation: str,
    actor: Actor,
    resource: object | None = None,
) -> None:
    """Evaluate a policy and reject both unconfigured and explicit denials."""

    selected = policy or DEFAULT_POLICY
    try:
        allowed = selected.authorize(operation, actor, resource)
    except PolicyNotConfigured:
        raise
    if not allowed:
        raise AuthorizationDenied(f"The actor may not perform {operation}.")
