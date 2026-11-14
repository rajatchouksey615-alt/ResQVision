import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.responses.models import (
    AssignmentStatusHistory,
    Response,
    ResponseAssignment,
)


@pytest.mark.django_db
def test_police_and_hospital_assignments_have_independent_lifecycles(
    incident, user, police_organization, hospital_organization
):
    police = ResponseAssignment.objects.create(
        incident=incident,
        target_organization=police_organization,
        assigned_by_user=user,
    )
    hospital = ResponseAssignment.objects.create(
        incident=incident,
        target_organization=hospital_organization,
        assigned_by_user=user,
    )
    police.status = ResponseAssignment.Status.ACKNOWLEDGED
    police.save(update_fields=["status", "updated_at"])

    hospital.refresh_from_db()
    assert police.status == ResponseAssignment.Status.ACKNOWLEDGED
    assert hospital.status == ResponseAssignment.Status.PENDING


@pytest.mark.django_db
def test_only_one_active_assignment_per_incident_and_target(incident, user, police_organization):
    ResponseAssignment.objects.create(
        incident=incident,
        target_organization=police_organization,
        assigned_by_user=user,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ResponseAssignment.objects.create(
                incident=incident,
                target_organization=police_organization,
                assigned_by_user=user,
            )


@pytest.mark.django_db
def test_assignment_command_id_is_idempotent(incident, user, police_organization):
    command_id = uuid.uuid4()
    ResponseAssignment.objects.create(
        incident=incident,
        target_organization=police_organization,
        assigned_by_user=user,
        creation_command_id=command_id,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ResponseAssignment.objects.create(
                incident=incident,
                target_organization=police_organization,
                assigned_by_user=user,
                creation_command_id=command_id,
            )


@pytest.mark.django_db
def test_assignment_history_requires_initial_pending_and_one_actor(
    incident, user, police_organization
):
    assignment = ResponseAssignment.objects.create(
        incident=incident,
        target_organization=police_organization,
        assigned_by_user=user,
    )
    history = AssignmentStatusHistory.objects.create(
        response_assignment=assignment,
        to_status=AssignmentStatusHistory.Status.PENDING,
        changed_by_user=user,
        occurred_at=timezone.now(),
    )

    with pytest.raises(ValidationError, match="append-only"):
        history.delete()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AssignmentStatusHistory.objects.create(
                response_assignment=assignment,
                from_status=AssignmentStatusHistory.Status.PENDING,
                to_status=AssignmentStatusHistory.Status.CANCELLED,
                reason="Replacement",
            )


@pytest.mark.django_db
def test_response_activity_is_append_only_and_command_is_unique(
    incident, user, police_organization
):
    assignment = ResponseAssignment.objects.create(
        incident=incident,
        target_organization=police_organization,
        assigned_by_user=user,
    )
    command_id = uuid.uuid4()
    activity = Response.objects.create(
        response_assignment=assignment,
        actor_user=user,
        activity_kind=Response.ActivityKind.PROGRESS_UPDATE,
        details="Simulated response progress.",
        command_id=command_id,
    )

    with pytest.raises(ValidationError, match="append-only"):
        activity.save()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Response.objects.create(
                response_assignment=assignment,
                actor_user=user,
                activity_kind=Response.ActivityKind.GENERAL_NOTE,
                command_id=command_id,
            )
