"""Fixtures for testing."""

import tracemalloc
import pytest

# Enable tracemalloc to get better error reporting for coroutine issues
tracemalloc.start()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    return
