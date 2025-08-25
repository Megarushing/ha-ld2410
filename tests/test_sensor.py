"""Test the sensors."""

import pytest
from unittest.mock import AsyncMock, PropertyMock, patch

from homeassistant.components.sensor import SensorDeviceClass
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
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from . import LD2410b_SERVICE_INFO

try:
    from tests.common import MockConfigEntry
except ImportError:
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import inject_bluetooth_service_info
except ImportError:
    from .mocks import inject_bluetooth_service_info


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

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    version_sensor = hass.states.get("sensor.test_name_firmware_version")
    version_attrs = version_sensor.attributes
    assert version_sensor.state == "2.44.24073110"
    assert version_attrs[ATTR_FRIENDLY_NAME] == "test-name Firmware version"

    build_sensor = hass.states.get("sensor.test_name_firmware_build_date")
    build_attrs = build_sensor.attributes
    assert build_sensor.state == "2024-07-31T10:00:00+00:00"
    assert build_attrs[ATTR_FRIENDLY_NAME] == "test-name Firmware build date"
    assert build_attrs[ATTR_DEVICE_CLASS] == SensorDeviceClass.TIMESTAMP

    rssi_sensor = hass.states.get("sensor.test_name_signal_strength")
    rssi_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-90"
    assert rssi_attrs[ATTR_FRIENDLY_NAME] == "test-name Signal strength"
    assert rssi_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entities_created_without_initial_data(hass: HomeAssistant) -> None:
    """Test entities are added even when no initial data is available."""
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

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.parsed_data",
            new_callable=PropertyMock,
            return_value={},
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.test_name_motion") is not None
    assert hass.states.get("sensor.test_name_firmware_version") is not None
    for gate in range(9):
        move = hass.states.get(f"sensor.test_name_moving_gate_{gate}_energy")
        still = hass.states.get(f"sensor.test_name_still_gate_{gate}_energy")
        assert move is not None
        assert move.state == STATE_UNKNOWN
        assert still is not None
        assert still.state == STATE_UNKNOWN


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_gate_energy_sensors(hass: HomeAssistant) -> None:
    """Test gate energy sensors report values when data is present."""
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

    mock_parsed = {
        "firmware_version": "2.44.24073110",
        "firmware_build_date": "2024-07-31T10:00:00+00:00",
        "move_gate_energy": list(range(1, 10)),
        "still_gate_energy": list(range(9, 0, -1)),
    }

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value=mock_parsed),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    for gate in range(9):
        move = hass.states.get(f"sensor.test_name_moving_gate_{gate}_energy")
        still = hass.states.get(f"sensor.test_name_still_gate_{gate}_energy")
        assert move is not None
        assert move.state == str(mock_parsed["move_gate_energy"][gate])
        assert still is not None
        assert still.state == str(mock_parsed["still_gate_energy"][gate])


async def test_frame_type_sensor_disabled_by_default(hass: HomeAssistant) -> None:
    """Ensure the frame type sensor is disabled by default."""
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

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    entity_id = "sensor.test_name_frame_type"
    entity = registry.async_get(entity_id)
    assert entity
    assert entity.disabled
    assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None
