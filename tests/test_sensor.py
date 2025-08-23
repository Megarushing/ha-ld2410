"""Test the ld2410 sensors."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.sensor import ATTR_STATE_CLASS
from custom_components.ld2410.const import (
    DOMAIN,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSOR_TYPE,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from . import (
    LD2410b_SERVICE_INFO,
    LD2410b_2_SERVICE_INFO
)

try:
    from tests.common import MockConfigEntry
except ImportError:
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import (
        inject_bluetooth_service_info
    )
except ImportError:
    from .mocks import (
        inject_bluetooth_service_info
    )

@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(hass: HomeAssistant) -> None:
    """Test setting up creates the sensors."""
    await async_setup_component(hass, DOMAIN, {})
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "test-password",
            CONF_SENSOR_TYPE: "ld2410",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_all("sensor")) == 1

    rssi_sensor = hass.states.get("sensor.test_name_signal_strength")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-90"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == 'test-name Signal strength'
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

