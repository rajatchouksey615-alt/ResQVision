import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

User = get_user_model()


@pytest.mark.django_db
def test_local_fixture_command_requires_explicit_opt_in_without_writes(monkeypatch):
    monkeypatch.delenv("RESQVISION_LOCAL_TEST_DATA_OPT_IN", raising=False)
    with override_settings(DEBUG=True):
        users_before = User.objects.count()
        with pytest.raises(CommandError, match="opt in to local fixture creation"):
            call_command("setup_local_dashboard_test_data", verbosity=0)
        assert User.objects.count() == users_before


@pytest.mark.django_db
def test_local_fixture_command_refuses_debug_false_without_writes(monkeypatch):
    monkeypatch.setenv("RESQVISION_LOCAL_TEST_DATA_OPT_IN", "1")
    users_before = User.objects.count()
    with override_settings(DEBUG=False):
        with pytest.raises(CommandError, match="unless DEBUG=True"):
            call_command("setup_local_dashboard_test_data", verbosity=0)
    assert User.objects.count() == users_before
