"""Small typed results for service commands."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandResult[T]:
    value: T
    replayed: bool = False
