import django.db.models.deletion
import django.db.models.functions.text
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
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
                ("code", models.CharField(max_length=80)),
                ("display_name", models.CharField(max_length=200)),
                (
                    "organization_kind",
                    models.CharField(
                        choices=[
                            ("POLICE", "Police"),
                            ("HOSPITAL", "Hospital"),
                            ("SOURCE_OWNER", "Source owner"),
                            ("OTHER", "Other"),
                        ],
                        max_length=24,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "organizations_organization",
                "indexes": [
                    models.Index(
                        fields=["organization_kind", "is_active"],
                        name="ix_organization_kind_active",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("code",), name="uq_organization_code"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "organization_kind__in",
                                ["POLICE", "HOSPITAL", "SOURCE_OWNER", "OTHER"],
                            ),
                            (
                                "code",
                                django.db.models.functions.text.Lower(
                                    django.db.models.functions.text.Trim("code")
                                ),
                            ),
                            models.Q(("code", ""), _negated=True),
                            models.Q(("display_name__regex", "^\\s*$"), _negated=True),
                        ),
                        name="ck_org_kind",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="OrganizationMembership",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("SUSPENDED", "Suspended"),
                            ("REVOKED", "Revoked"),
                        ],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="memberships",
                        to="organizations.organization",
                    ),
                ),
                (
                    "role_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="organization_memberships",
                        to="auth.group",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="organization_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "organizations_membership",
                "indexes": [
                    models.Index(
                        fields=["organization", "role_group", "status"],
                        name="ix_membership_org_role_active",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "organization", "role_group"),
                        name="uq_org_membership_scope",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("status__in", ["ACTIVE", "SUSPENDED", "REVOKED"])
                        ),
                        name="ck_membership_status",
                    ),
                ],
            },
        ),
    ]
