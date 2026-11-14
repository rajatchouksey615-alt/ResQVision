import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VideoSource",
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
                ("source_code", models.CharField(max_length=128)),
                ("name", models.CharField(max_length=200)),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("CONTROLLED_FILE", "Controlled file"),
                            ("CAMERA_STREAM", "Camera stream"),
                            ("OTHER", "Other"),
                        ],
                        max_length=24,
                    ),
                ),
                (
                    "owner_external_ref",
                    models.CharField(blank=True, max_length=128, null=True),
                ),
                (
                    "authorization_status",
                    models.CharField(
                        choices=[
                            ("PENDING_REVIEW", "Pending review"),
                            ("AUTHORIZED", "Authorized"),
                            ("SUSPENDED", "Suspended"),
                            ("REVOKED", "Revoked"),
                        ],
                        default="PENDING_REVIEW",
                        max_length=20,
                    ),
                ),
                (
                    "availability_status",
                    models.CharField(
                        choices=[
                            ("UNKNOWN", "Unknown"),
                            ("AVAILABLE", "Available"),
                            ("DEGRADED", "Degraded"),
                            ("UNAVAILABLE", "Unavailable"),
                        ],
                        default="UNKNOWN",
                        max_length=16,
                    ),
                ),
                ("authorized_at", models.DateTimeField(blank=True, null=True)),
                (
                    "authorization_reference",
                    models.CharField(blank=True, max_length=256, null=True),
                ),
                (
                    "configuration_ref",
                    models.CharField(blank=True, max_length=256, null=True),
                ),
                ("processing_policy_ref", models.CharField(max_length=100)),
                ("retention_policy_ref", models.CharField(max_length=100)),
                ("last_health_check_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "authorized_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="authorized_video_sources",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner_organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="video_sources",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "db_table": "sources_video_source",
                "indexes": [
                    models.Index(
                        fields=[
                            "authorization_status",
                            "availability_status",
                            "updated_at",
                        ],
                        name="ix_source_auth_availability",
                    ),
                    models.Index(
                        fields=["availability_status", "last_health_check_at"],
                        name="ix_source_availability_health",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source_code",), name="uq_video_source_code"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "source_type__in",
                                ["CONTROLLED_FILE", "CAMERA_STREAM", "OTHER"],
                            )
                        ),
                        name="ck_source_type",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "authorization_status__in",
                                [
                                    "PENDING_REVIEW",
                                    "AUTHORIZED",
                                    "SUSPENDED",
                                    "REVOKED",
                                ],
                            ),
                            (
                                "availability_status__in",
                                ["UNKNOWN", "AVAILABLE", "DEGRADED", "UNAVAILABLE"],
                            ),
                            models.Q(
                                models.Q(
                                    ("authorization_status", "AUTHORIZED"),
                                    ("authorized_at__isnull", False),
                                    ("authorized_by_user__isnull", False),
                                ),
                                models.Q(
                                    models.Q(
                                        ("authorization_status", "AUTHORIZED"),
                                        _negated=True,
                                    ),
                                    ("authorized_at__isnull", True),
                                    ("authorized_by_user__isnull", True),
                                ),
                                _connector="OR",
                            ),
                        ),
                        name="ck_source_states",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("owner_organization__isnull", False),
                            models.Q(
                                ("owner_external_ref__isnull", False),
                                models.Q(("owner_external_ref", ""), _negated=True),
                                models.Q(
                                    ("owner_external_ref__regex", "^\\s*$"),
                                    _negated=True,
                                ),
                            ),
                            _connector="OR",
                        ),
                        name="ck_source_owner_ref",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("source_code__regex", "^\\s*$"), _negated=True),
                            models.Q(("name__regex", "^\\s*$"), _negated=True),
                            models.Q(
                                ("processing_policy_ref__regex", "^\\s*$"),
                                _negated=True,
                            ),
                            models.Q(
                                ("retention_policy_ref__regex", "^\\s*$"), _negated=True
                            ),
                        ),
                        name="ck_source_nonblank_fields",
                    ),
                ],
            },
        ),
    ]
