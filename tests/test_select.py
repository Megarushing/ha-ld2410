"""Test the resolution select entity."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.ld2410.const import DOMAIN

from . import LD2410b_SERVICE_INFO

try:
    from tests.common import MockConfigEntry
except ImportError:  # Home Assistant <2023.9
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import inject_bluetooth_service_info
except ImportError:  # Home Assistant <2023.9
    from .mocks import inject_bluetooth_service_info


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_resolution_select(hass: HomeAssistant) -> None:
    """Test resolution select entity."""
    await async_setup_component(hass, DOMAIN, {})
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "name": "test-name",
            "password": "test-password",
            "sensor_type": "ld2410",
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
        patch("custom_components.ld2410.api.LD2410.connect_and_update", AsyncMock()),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value={"resolution": 0}),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_set_resolution",
            AsyncMock(),
        ) as set_mock,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

        entity_id = "select.test_name_distance_resolution"
        state = hass.states.get(entity_id)
        assert state and state.state == "0.75 m"

        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": "0.20 m"},
            blocking=True,
        )
        set_mock.assert_awaited_once_with(1)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_light_function_select(hass: HomeAssistant) -> None:
    """Test light function select entity."""
    await async_setup_component(hass, DOMAIN, {})
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "name": "test-name",
            "password": "test-password",
            "sensor_type": "ld2410",
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
        patch("custom_components.ld2410.api.LD2410.connect_and_update", AsyncMock()),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value={"light_function": True, "light_threshold": 100}),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_set_light_function",
            AsyncMock(),
        ) as set_mock,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

        entity_id = "select.test_name_light_function"
        state = hass.states.get(entity_id)
        assert state and state.state == "on"

        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": "off"},
            blocking=True,
        )
        set_mock.assert_awaited_once_with(False)
