"""Test LD2410 sensors."""

from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from . import (
    DOMAIN,
    ENTRY_CONFIG,
    LD2410_SERVICE_INFO,
    MockConfigEntry,
)


def test_service_info_creation():
    """Test that service info can be created properly."""
    assert LD2410_SERVICE_INFO is not None
    assert LD2410_SERVICE_INFO.name.startswith("HLK-LD2410")
    assert len(LD2410_SERVICE_INFO.address) == 17  # MAC address length


async def test_sensor_basic_setup(hass: HomeAssistant) -> None:
    """Test basic sensor setup without full HA integration."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_CONFIG)
    
    # For now, just test that we can create a config entry
    # Later we can add tests when sensor.py is implemented
    assert entry.domain == DOMAIN
    assert "address" in entry.data
