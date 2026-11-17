"""Isolate the shared DRF throttle cache between API test cases."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def isolate_api_throttle_cache():
    cache.clear()
    yield
    cache.clear()
