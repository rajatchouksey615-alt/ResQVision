import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent


@pytest.mark.django_db
def test_human_audit_event_keeps_a_non_secret_actor_snapshot():
    user = User.objects.create_user("reviewer@example.com", "local-test-password")
    event = AuditEvent.objects.create(
        actor_user=user,
        actor_kind=AuditEvent.ActorKind.HUMAN,
        actor_ref_snapshot=str(user.pk),
        resource_type=AuditEvent.ResourceType.AUTHENTICATION,
        action="AUTHENTICATION_SUCCESS",
        outcome=AuditEvent.Outcome.SUCCESS,
        occurred_at=timezone.now(),
    )

    assert event.actor_ref_snapshot == str(user.pk)
    assert event.safe_context == {}


@pytest.mark.django_db
def test_audit_event_model_and_queryset_are_append_only():
    event = AuditEvent.objects.create(
        actor_kind=AuditEvent.ActorKind.ANONYMOUS,
        actor_ref_snapshot="ANONYMOUS",
        resource_type=AuditEvent.ResourceType.AUTHENTICATION,
        action="AUTHENTICATION_DENIED",
        outcome=AuditEvent.Outcome.DENIED,
        occurred_at=timezone.now(),
    )

    event.action = "CHANGED"
    with pytest.raises(ValidationError, match="append-only"):
        event.save()
    with pytest.raises(ValidationError, match="append-only"):
        AuditEvent.objects.filter(pk=event.pk).update(action="CHANGED")
    with pytest.raises(ValidationError, match="append-only"):
        AuditEvent.objects.filter(pk=event.pk).delete()


@pytest.mark.django_db
def test_audit_actor_kind_check_rejects_machine_without_service_reference():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AuditEvent.objects.create(
                actor_kind=AuditEvent.ActorKind.MACHINE,
                actor_ref_snapshot="AI_SERVICE",
                resource_type=AuditEvent.ResourceType.DETECTION_EVENT,
                action="DETECTION_EVENT_ACCEPTED",
                outcome=AuditEvent.Outcome.SUCCESS,
                occurred_at=timezone.now(),
            )


@pytest.mark.django_db
def test_audit_context_must_be_a_json_object_in_postgresql():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AuditEvent.objects.bulk_create(
                [
                    AuditEvent(
                        actor_kind=AuditEvent.ActorKind.ANONYMOUS,
                        actor_ref_snapshot="ANONYMOUS",
                        resource_type=AuditEvent.ResourceType.AUTHENTICATION,
                        action="AUTHENTICATION_DENIED",
                        outcome=AuditEvent.Outcome.DENIED,
                        safe_context=["not", "an", "object"],
                        occurred_at=timezone.now(),
                    )
                ]
            )
