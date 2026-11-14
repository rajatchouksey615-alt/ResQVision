import django.db.models.deletion
import django.db.models.lookups
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "actor_kind",
                    models.CharField(
                        choices=[
                            ("HUMAN", "Human"),
                            ("MACHINE", "Machine"),
                            ("ANONYMOUS", "Anonymous"),
                        ],
                        max_length=12,
                    ),
                ),
                (
                    "actor_service_ref",
                    models.CharField(blank=True, max_length=128, null=True),
                ),
                ("actor_ref_snapshot", models.CharField(max_length=128)),
                (
                    "resource_type",
                    models.CharField(
                        choices=[
                            ("USER", "User"),
                            ("ORGANIZATION", "Organization"),
                            ("MEMBERSHIP", "Membership"),
                            ("VIDEO_SOURCE", "Video source"),
                            ("DETECTION_EVENT", "Detection event"),
                            ("CANDIDATE", "Candidate"),
                            ("INCIDENT", "Incident"),
                            ("ASSIGNMENT", "Assignment"),
                            ("EVIDENCE", "Evidence"),
                            ("LOCATION", "Location"),
                            ("NOTIFICATION", "Notification"),
                            ("AUTHENTICATION", "Authentication"),
                        ],
                        max_length=32,
                    ),
                ),
                ("resource_id", models.UUIDField(blank=True, null=True)),
                ("action", models.CharField(max_length=80)),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("SUCCESS", "Success"),
                            ("DENIED", "Denied"),
                            ("FAILED", "Failed"),
                            ("SIMULATED", "Simulated"),
                        ],
                        max_length=16,
                    ),
                ),
                ("request_id", models.UUIDField(blank=True, null=True)),
                ("context_schema_version", models.PositiveSmallIntegerField(default=1)),
                ("safe_context", models.JSONField(default=dict)),
                (
                    "occurred_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "actor_user",
                    models.ForeignKey(
                        blank=True,
                        db_index=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "audit_audit_event",
                "indexes": [
                    models.Index(fields=["occurred_at"], name="ix_audit_occurred"),
                    models.Index(
                        fields=["action", "occurred_at"], name="ix_audit_action_time"
                    ),
                    models.Index(
                        fields=["resource_type", "resource_id", "occurred_at"],
                        name="ix_audit_resource_time",
                    ),
                    models.Index(
                        fields=["actor_user", "occurred_at"],
                        name="ix_audit_human_actor_time",
                    ),
                    models.Index(
                        fields=["actor_service_ref", "occurred_at"],
                        name="ix_audit_machine_actor_time",
                    ),
                    models.Index(fields=["request_id"], name="ix_audit_request_id"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                models.Q(
                                    ("actor_kind", "HUMAN"),
                                    ("actor_service_ref__isnull", True),
                                ),
                                models.Q(
                                    ("actor_kind", "MACHINE"),
                                    (
                                        "actor_ref_snapshot",
                                        models.F("actor_service_ref"),
                                    ),
                                    ("actor_service_ref__isnull", False),
                                    ("actor_user__isnull", True),
                                ),
                                models.Q(
                                    ("actor_kind", "ANONYMOUS"),
                                    ("actor_ref_snapshot", "ANONYMOUS"),
                                    ("actor_service_ref__isnull", True),
                                    ("actor_user__isnull", True),
                                ),
                                _connector="OR",
                            ),
                            models.Q(
                                ("actor_ref_snapshot__regex", "^\\s*$"), _negated=True
                            ),
                        ),
                        name="ck_audit_actor_kind",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "resource_type__in",
                                [
                                    "USER",
                                    "ORGANIZATION",
                                    "MEMBERSHIP",
                                    "VIDEO_SOURCE",
                                    "DETECTION_EVENT",
                                    "CANDIDATE",
                                    "INCIDENT",
                                    "ASSIGNMENT",
                                    "EVIDENCE",
                                    "LOCATION",
                                    "NOTIFICATION",
                                    "AUTHENTICATION",
                                ],
                            )
                        ),
                        name="ck_audit_target",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "outcome__in",
                                ["SUCCESS", "DENIED", "FAILED", "SIMULATED"],
                            )
                        ),
                        name="ck_audit_outcome",
                    ),
                    models.CheckConstraint(
                        condition=django.db.models.lookups.Exact(
                            models.Func(
                                models.F("safe_context"),
                                function="jsonb_typeof",
                                output_field=models.CharField(),
                            ),
                            models.Value("object"),
                        ),
                        name="ck_audit_context_object",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("context_schema_version__gte", 1)),
                        name="ck_audit_context_version",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("action__regex", "^\\S+$")),
                        name="ck_audit_action_nonblank",
                    ),
                ],
            },
        ),
    ]
