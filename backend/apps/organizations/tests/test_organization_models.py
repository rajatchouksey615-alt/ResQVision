import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership


@pytest.mark.django_db
def test_organization_normalizes_code_and_uses_uuid_primary_key():
    organization = Organization.objects.create(
        code="  CENTRAL-POLICE  ",
        display_name="  Central Police  ",
        organization_kind=Organization.Kind.POLICE,
    )

    assert organization.code == "central-police"
    assert organization.display_name == "Central Police"
    assert organization.pk.version == 4


@pytest.mark.django_db
def test_organization_code_is_unique_in_postgresql():
    Organization.objects.create(
        code="central-police",
        display_name="Central Police",
        organization_kind=Organization.Kind.POLICE,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Organization.objects.create(
                code="central-police",
                display_name="Duplicate Police",
                organization_kind=Organization.Kind.POLICE,
            )


@pytest.mark.django_db
def test_membership_scopes_a_seeded_police_group_to_one_organization():
    user = User.objects.create_user("police@example.com", "local-test-password")
    organization = Organization.objects.create(
        code="central-police",
        display_name="Central Police",
        organization_kind=Organization.Kind.POLICE,
    )
    police_group = Group.objects.get(name="POLICE")
    membership = OrganizationMembership.objects.create(
        user=user,
        organization=organization,
        role_group=police_group,
    )

    assert membership.status == OrganizationMembership.Status.ACTIVE
    assert membership.role_group_id == police_group.pk
    assert (
        OrganizationMembership._meta.get_field("role_group").target_field is police_group._meta.pk
    )


@pytest.mark.django_db
def test_membership_rejects_global_admin_group():
    user = User.objects.create_user("admin@example.com", "local-test-password")
    organization = Organization.objects.create(
        code="central-police",
        display_name="Central Police",
        organization_kind=Organization.Kind.POLICE,
    )
    membership = OrganizationMembership(
        user=user,
        organization=organization,
        role_group=Group.objects.get(name="ADMIN"),
    )

    with pytest.raises(ValidationError, match="Only Police and Hospital groups"):
        membership.full_clean()


@pytest.mark.django_db
def test_membership_rejects_role_group_that_does_not_match_organization_kind():
    user = User.objects.create_user("hospital@example.com", "local-test-password")
    organization = Organization.objects.create(
        code="central-hospital",
        display_name="Central Hospital",
        organization_kind=Organization.Kind.HOSPITAL,
    )
    membership = OrganizationMembership(
        user=user,
        organization=organization,
        role_group=Group.objects.get(name="POLICE"),
    )

    with pytest.raises(ValidationError, match="must match the organization kind"):
        membership.full_clean()
