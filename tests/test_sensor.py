"""Test the sensors."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

from homeassistant.components.sensor import SensorDeviceClass
from custom_components.ld2410.const import (
    DOMAIN,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    CONF_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSOR_TYPE,
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
        patch(
            "custom_components.ld2410.api.LD2410.connect_and_update",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(
                return_value={
                    "firmware_version": "2.44.24073110",
                    "firmware_build_date": datetime(
                        2024, 7, 31, 10, 0, tzinfo=timezone.utc
                    ),
                }
            ),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
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

    registry = er.async_get(hass)
    assert registry.async_get("sensor.test_name_signal_strength") is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_rssi_sensor_updates_via_connection(hass: HomeAssistant) -> None:
    """RSSI sensor should poll the device for current signal strength."""
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
            "custom_components.ld2410.api.LD2410.connect_and_update",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value={}),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()
        sensor_id = "sensor.test_name_signal_strength"
        registry = er.async_get(hass)
        registry.async_update_entity(sensor_id, disabled_by=None)
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()
        await hass.helpers.entity_component.async_update_entity(sensor_id)

        assert hass.states.get(sensor_id) is not None

        device = entry.runtime_data.device

        async def mock_read_rssi() -> int:
            device._rssi = -70
            return -70

        with patch.object(device, "read_rssi", mock_read_rssi):
            await hass.helpers.entity_component.async_update_entity(sensor_id)

        assert hass.states.get(sensor_id).state == "-70"


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
            "custom_components.ld2410.api.LD2410.connect_and_update",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.parsed_data",
            new_callable=PropertyMock,
            return_value={},
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value={}),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    assert registry.async_get("binary_sensor.test_name_motion") is not None
    assert registry.async_get("binary_sensor.test_name_out_pin") is not None
    assert registry.async_get("sensor.test_name_photo_sensor") is not None
    assert registry.async_get("sensor.test_name_firmware_version") is not None
    for gate in range(9):
        assert (
            registry.async_get(f"sensor.test_name_motion_gate_{gate}_energy")
            is not None
        )
        assert (
            registry.async_get(f"sensor.test_name_still_gate_{gate}_energy") is not None
        )


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
        "firmware_build_date": datetime(2024, 7, 31, 10, 0, tzinfo=timezone.utc),
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
            "custom_components.ld2410.api.LD2410.connect_and_update",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value=mock_parsed),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

    coordinator = entry.runtime_data
    for gate in range(9):
        assert (
            coordinator.device.parsed_data["move_gate_energy"][gate]
            == mock_parsed["move_gate_energy"][gate]
        )
        assert (
            coordinator.device.parsed_data["still_gate_energy"][gate]
            == mock_parsed["still_gate_energy"][gate]
        )


async def test_photo_and_out_pin_sensors(hass: HomeAssistant) -> None:
    """Ensure photo sensor and OUT pin report values."""
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
        "firmware_build_date": datetime(2024, 7, 31, 10, 0, tzinfo=timezone.utc),
        "photo_sensor": 123,
        "out_pin": True,
    }

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.connect_and_update",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value=mock_parsed),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        entity_id = "sensor.test_name_photo_sensor"
        registry.async_update_entity(entity_id, disabled_by=None)
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = entry.runtime_data
        coordinator.device._update_parsed_data(mock_parsed)
        coordinator.device._fire_callbacks()
        assert hass.states.get(entity_id).state == str(mock_parsed["photo_sensor"])


async def test_frame_type_and_photo_sensors_disabled_by_default(
    hass: HomeAssistant,
) -> None:
    """Ensure the frame type and photo sensors are disabled by default."""
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
            "custom_components.ld2410.api.LD2410.connect_and_update",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(
                return_value={
                    "firmware_version": "2.44.24073110",
                    "firmware_build_date": datetime(
                        2024, 7, 31, 10, 0, tzinfo=timezone.utc
                    ),
                }
            ),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    for sensor in ("frame_type", "photo_sensor"):
        entity_id = f"sensor.test_name_{sensor}"
        entity = registry.async_get(entity_id)
        assert entity
        assert entity.disabled
        assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
        assert hass.states.get(entity_id) is None
