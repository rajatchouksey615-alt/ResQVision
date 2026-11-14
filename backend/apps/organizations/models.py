"""Agency/source-owner records and organization-scoped human memberships."""

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower, Trim

from common.models import UUIDPrimaryKeyModel


class OrganizationKind(models.TextChoices):
    POLICE = "POLICE", "Police"
    HOSPITAL = "HOSPITAL", "Hospital"
    SOURCE_OWNER = "SOURCE_OWNER", "Source owner"
    OTHER = "OTHER", "Other"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    REVOKED = "REVOKED", "Revoked"


class Organization(UUIDPrimaryKeyModel):
    Kind = OrganizationKind

    code = models.CharField(max_length=80)
    display_name = models.CharField(max_length=200)
    organization_kind = models.CharField(max_length=24, choices=OrganizationKind.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_organization"
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_organization_code"),
            models.CheckConstraint(
                condition=(
                    Q(organization_kind__in=OrganizationKind.values)
                    & Q(code=Lower(Trim("code")))
                    & ~Q(code="")
                    & ~Q(display_name__regex=r"^\s*$")
                ),
                name="ck_org_kind",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization_kind", "is_active"],
                name="ix_organization_kind_active",
            )
        ]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().lower()
        self.display_name = self.display_name.strip()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.display_name


class OrganizationMembership(UUIDPrimaryKeyModel):
    Status = MembershipStatus

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="organization_memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="memberships",
    )
    role_group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name="organization_memberships",
    )
    status = models.CharField(
        max_length=16,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization", "role_group"],
                name="uq_org_membership_scope",
            ),
            models.CheckConstraint(
                condition=Q(status__in=MembershipStatus.values),
                name="ck_membership_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "role_group", "status"],
                name="ix_membership_org_role_active",
            )
        ]

    def clean(self):
        super().clean()
        if not self.role_group_id or not self.organization_id:
            return
        if self.role_group.name not in {"POLICE", "HOSPITAL"}:
            raise ValidationError({"role_group": "Only Police and Hospital groups are scoped."})
        if self.organization.organization_kind != self.role_group.name:
            raise ValidationError(
                {"role_group": "The membership group must match the organization kind."}
            )

    def __str__(self) -> str:
        return f"{self.user_id} at {self.organization.code} ({self.role_group.name})"
