"""Fixtures for testing."""

import tracemalloc
import pytest
from unittest.mock import AsyncMock

# Enable tracemalloc to get better error reporting for coroutine issues
tracemalloc.start()


class AwaitableAsyncMock(AsyncMock):
    """AsyncMock that properly handles return values to avoid unawaited coroutines."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure the return value is set to avoid creating unawaited coroutines
        if 'return_value' not in kwargs:
            self.return_value = None


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    return
