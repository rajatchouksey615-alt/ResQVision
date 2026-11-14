import uuid

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notifications.models import Notification, NotificationDeliveryAttempt
from apps.responses.models import ResponseAssignment


@pytest.mark.django_db
def test_notification_targets_one_incident_or_assignment(incident, user):
    notification = Notification.objects.create(
        recipient_user=user,
        incident=incident,
        safe_message_code="INCIDENT_CREATED",
    )

    assert notification.response_assignment_id is None
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Notification.objects.create(
                recipient_user=user,
                safe_message_code="INVALID_TARGET",
            )


@pytest.mark.django_db
def test_notification_creation_command_is_idempotent(incident, user):
    command_id = uuid.uuid4()
    Notification.objects.create(
        recipient_user=user,
        incident=incident,
        creation_command_id=command_id,
        safe_message_code="INCIDENT_CREATED",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Notification.objects.create(
                recipient_user=user,
                incident=incident,
                creation_command_id=command_id,
                safe_message_code="INCIDENT_CREATED",
            )


@pytest.mark.django_db
def test_read_notification_requires_read_timestamp(incident, user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Notification.objects.create(
                recipient_user=user,
                incident=incident,
                status=Notification.Status.READ,
                safe_message_code="INCIDENT_CREATED",
            )


@pytest.mark.django_db
def test_delivery_failure_is_separate_and_requires_safe_failure_code(
    incident, user, police_organization
):
    assignment = ResponseAssignment.objects.create(
        incident=incident,
        target_organization=police_organization,
        assigned_by_user=user,
    )
    notification = Notification.objects.create(
        recipient_user=user,
        response_assignment=assignment,
        safe_message_code="ASSIGNMENT_PENDING",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            NotificationDeliveryAttempt.objects.create(
                notification=notification,
                attempt_number=1,
                outcome=NotificationDeliveryAttempt.Outcome.FAILED,
                attempted_at=timezone.now(),
            )

    attempt = NotificationDeliveryAttempt.objects.create(
        notification=notification,
        attempt_number=1,
        outcome=NotificationDeliveryAttempt.Outcome.FAILED,
        safe_failure_code="SIMULATED_UNAVAILABLE",
    )
    assert notification.status == Notification.Status.CREATED
    assert attempt.outcome == NotificationDeliveryAttempt.Outcome.FAILED


@pytest.mark.django_db
def test_delivery_attempt_number_is_unique_per_notification(incident, user):
    notification = Notification.objects.create(
        recipient_user=user,
        incident=incident,
        safe_message_code="INCIDENT_CREATED",
    )
    NotificationDeliveryAttempt.objects.create(
        notification=notification,
        attempt_number=1,
        outcome=NotificationDeliveryAttempt.Outcome.DELIVERED_SIMULATED,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            NotificationDeliveryAttempt.objects.create(
                notification=notification,
                attempt_number=1,
                outcome=NotificationDeliveryAttempt.Outcome.CANCELLED,
            )
