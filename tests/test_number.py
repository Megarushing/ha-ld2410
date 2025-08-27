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
            "custom_components.ld2410.api.LD2410.connect_and_subscribe",
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
            move_id = f"number.test_name_motion_gate_{gate}_sensitivity"
            still_id = f"number.test_name_static_gate_{gate}_sensitivity"
            assert hass.states.get(move_id).state == str(10 + gate)
            assert hass.states.get(still_id).state == str(20 + gate)

        await hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": "number.test_name_motion_gate_0_sensitivity",
                "value": 55,
            },
            blocking=True,
        )

        set_mock.assert_awaited_once_with(0, 55, 20)
