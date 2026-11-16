"""Errors raised when a domain command cannot be completed."""


class DomainError(Exception):
    """Base class for expected domain failures."""


class AuthorizationDenied(DomainError):
    """The actor is not permitted to perform an operation."""


class ResourceNotFound(DomainError):
    """A requested resource does not exist or is outside the actor's scope."""


class InvalidStateTransition(DomainError):
    """A resource cannot move from its current state to the requested state."""


class IdempotencyConflict(DomainError):
    """A command identifier was reused with different intent."""


class PolicyNotConfigured(DomainError):
    """An operation depends on an authority policy that has not been approved."""


class BusinessRuleViolation(DomainError):
    """A request violates a domain invariant."""


class ResourceConflict(DomainError):
    """A resource conflicts with another persisted resource."""
