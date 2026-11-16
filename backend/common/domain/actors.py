"""Trusted actor contexts passed by an authenticated application boundary."""

from dataclasses import dataclass
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser


@dataclass(frozen=True, slots=True)
class HumanActor:
    """A human user resolved by a trusted authentication boundary."""

    user: AbstractBaseUser

    @property
    def user_id(self) -> UUID:
        return self.user.pk


@dataclass(frozen=True, slots=True)
class MachineActor:
    """A machine principal resolved by a trusted service-authentication boundary."""

    service_ref: str


@dataclass(frozen=True, slots=True)
class AnonymousActor:
    """An unauthenticated actor used only for safe audit events."""


type Actor = HumanActor | MachineActor | AnonymousActor
