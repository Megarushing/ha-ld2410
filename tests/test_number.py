"""Test gate sensitivity numbers."""

from datetime import datetime, timezone
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
async def test_gate_sensitivity_numbers(hass: HomeAssistant) -> None:
    """Test sliders for gate sensitivity."""
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

    mock_parsed = {
        "firmware_version": "2.44.24073110",
        "firmware_build_date": datetime(2024, 7, 31, 10, 0, tzinfo=timezone.utc),
        "move_gate_sensitivity": list(range(10, 19)),
        "still_gate_sensitivity": list(range(20, 29)),
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
        patch(
            "custom_components.ld2410.api.LD2410.cmd_set_gate_sensitivity",
            AsyncMock(),
        ) as set_mock,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

        for gate in range(9):
            move_id = f"number.test_name_mg{gate}_sensitivity"
            still_id = f"number.test_name_sg{gate}_sensitivity"
            assert hass.states.get(move_id).state == str(10 + gate)
            assert hass.states.get(still_id).state == str(20 + gate)

        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.test_name_mg0_sensitivity", "value": 55},
            blocking=True,
        )

        set_mock.assert_awaited_once_with(0, 55, 20)

        new_params = {
            "move_gate_sensitivity": [90] * 9,
            "still_gate_sensitivity": [80] * 9,
        }
        with (
            patch(
                "custom_components.ld2410.api.LD2410.cmd_auto_thresholds",
                AsyncMock(),
            ),
            patch(
                "custom_components.ld2410.api.LD2410.cmd_query_auto_thresholds",
                AsyncMock(side_effect=[1, 0]),
            ),
            patch(
                "custom_components.ld2410.api.LD2410.cmd_read_params",
                AsyncMock(return_value=new_params),
            ),
            patch("custom_components.ld2410.button.asyncio.sleep", AsyncMock()),
        ):
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.test_name_auto_threshold"},
                blocking=True,
            )
            await hass.async_block_till_done()

        assert hass.states.get("number.test_name_mg0_sensitivity").state == "90"
        assert hass.states.get("number.test_name_sg0_sensitivity").state == "80"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_light_sensitivity_number(hass: HomeAssistant) -> None:
    """Test light sensitivity slider."""
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
            AsyncMock(return_value={"light_threshold": 128, "light_function": True}),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_set_light_threshold",
            AsyncMock(),
        ) as set_mock,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

        entity_id = "number.test_name_light_sensitivity"
        state = hass.states.get(entity_id)
        assert state and state.state == "128"

        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id, "value": 200},
            blocking=True,
        )
        set_mock.assert_awaited_once_with(200)
