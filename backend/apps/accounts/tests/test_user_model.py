import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_user_manager_normalizes_email_and_hashes_password():
    user = User.objects.create_user("  ResQ.User@Example.COM  ", "not-a-plain-text-password")

    assert user.email == "resq.user@example.com"
    assert user.password != "not-a-plain-text-password"
    assert user.check_password("not-a-plain-text-password")


@pytest.mark.django_db
def test_user_manager_rejects_missing_email():
    with pytest.raises(ValueError, match="email address is required"):
        User.objects.create_user("  ", "irrelevant")


@pytest.mark.django_db
def test_superuser_manager_sets_required_privileges():
    user = User.objects.create_superuser("admin@example.com", "local-test-password")

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True


@pytest.mark.django_db
def test_superuser_manager_rejects_inconsistent_privilege_flags():
    with pytest.raises(ValueError, match="is_staff=True"):
        User.objects.create_superuser(
            "admin@example.com",
            "local-test-password",
            is_staff=False,
        )
