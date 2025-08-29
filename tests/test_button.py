"""Test the configuration button."""

from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.ld2410.const import (
    CONF_MOVE_THRESHOLDS,
    CONF_RETRY_COUNT,
    CONF_STILL_THRESHOLDS,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
)

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
async def test_auto_threshold_button(hass: HomeAssistant) -> None:
    """Test pressing the button starts auto threshold detection."""
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
            "custom_components.ld2410.api.devices.device.BaseDevice._ensure_connected",
            AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_engineering_mode",
            AsyncMock(),
        ),
        patch("custom_components.ld2410.api.LD2410._on_connect", AsyncMock()),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value={}),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_auto_thresholds", AsyncMock()
        ) as auto_mock,
        patch(
            "custom_components.ld2410.api.LD2410.cmd_query_auto_thresholds",
            AsyncMock(return_value=0),
        ) as query_mock,
        patch(
            "custom_components.ld2410.api.LD2410.cmd_read_params",
            AsyncMock(
                return_value={
                    "move_gate_sensitivity": [],
                    "still_gate_sensitivity": [],
                }
            ),
        ) as read_mock,
        patch(
            "custom_components.ld2410.button.asyncio.sleep", AsyncMock()
        ) as sleep_mock,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

        assert hass.states.get("button.test_name_auto_threshold") is not None

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.test_name_auto_threshold"},
            blocking=True,
        )

        auto_mock.assert_awaited_once_with(10)
        sleep_mock.assert_has_awaits([call(10)], any_order=True)
        query_mock.assert_awaited_once()
        read_mock.assert_awaited_once()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_save_thresholds_button(hass: HomeAssistant) -> None:
    """Test saving gate thresholds to options."""
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

    move = list(range(1, 10))
    still = list(range(11, 20))

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._ensure_connected",
            AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_engineering_mode",
            AsyncMock(),
        ),
        patch("custom_components.ld2410.api.LD2410._on_connect", AsyncMock()),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(
                return_value={
                    "move_gate_sensitivity": move,
                    "still_gate_sensitivity": still,
                }
            ),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

        with patch.object(hass.config_entries, "async_update_entry") as update_mock:
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.test_name_save_thresholds"},
                blocking=True,
            )

        update_mock.assert_called_once()
        opts = update_mock.call_args[1]["options"]
        assert opts[CONF_MOVE_THRESHOLDS] == move
        assert opts[CONF_STILL_THRESHOLDS] == still


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_load_thresholds_button(hass: HomeAssistant) -> None:
    """Test loading gate thresholds from options to device."""
    await async_setup_component(hass, DOMAIN, {})
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    move = list(range(1, 10))
    still = list(range(11, 20))

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "name": "test-name",
            "password": "test-password",
            "sensor_type": "ld2410",
        },
        options={
            CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
            CONF_MOVE_THRESHOLDS: move,
            CONF_STILL_THRESHOLDS: still,
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_hass(hass)

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._ensure_connected",
            AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_engineering_mode",
            AsyncMock(),
        ),
        patch("custom_components.ld2410.api.LD2410._on_connect", AsyncMock()),
        patch(
            "custom_components.ld2410.api.devices.device.Device.get_basic_info",
            AsyncMock(return_value={}),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_set_gate_sensitivity",
            AsyncMock(),
        ) as set_mock,
        patch(
            "custom_components.ld2410.api.devices.device.Device._fire_callbacks",
            Mock(),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.test_name_load_thresholds"},
            blocking=True,
        )

        expected = [call(i, move[i], still[i]) for i in range(9)]
        set_mock.assert_has_awaits(expected)
