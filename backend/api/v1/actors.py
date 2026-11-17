"""Resolve trusted domain actor values only from authenticated principals."""

from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotAuthenticated

from common.domain.actors import HumanActor, MachineActor


def get_human_actor(request) -> HumanActor:
    user_model = get_user_model()
    request_user = getattr(request, "user", None)
    if not isinstance(request_user, user_model) or not request_user.is_authenticated:
        raise NotAuthenticated
    user = user_model.objects.filter(pk=request_user.pk, is_active=True).first()
    if user is None:
        raise NotAuthenticated
    return HumanActor(user)


def get_machine_actor(request) -> MachineActor:
    actor = getattr(request, "user", None)
    if not isinstance(actor, MachineActor):
        raise NotAuthenticated
    return actor
