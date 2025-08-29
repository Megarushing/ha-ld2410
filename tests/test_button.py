"""Test the configuration button."""

from unittest.mock import AsyncMock, call, patch

import pytest

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.ld2410.const import (
    CONF_SAVED_MOVE_SENSITIVITY,
    CONF_SAVED_STILL_SENSITIVITY,
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
async def test_auto_sensitivities_button(hass: HomeAssistant) -> None:
    """Test pressing the button starts auto sensitivity detection."""
    await async_setup_component(hass, DOMAIN, {})
    await async_setup_component(hass, "persistent_notification", {})
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
        patch("custom_components.ld2410.button.async_call_later") as call_later_mock,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

        assert hass.states.get("button.test_name_auto_sensitivities") is not None

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.test_name_auto_sensitivities"},
            blocking=True,
        )
        await hass.async_block_till_done()

        auto_mock.assert_awaited_once_with(10)
        sleep_mock.assert_has_awaits([call(10)], any_order=True)
        query_mock.assert_awaited_once()
        read_mock.assert_awaited_once()
        call_later_mock.assert_called_once()
        assert call_later_mock.call_args[0][1] == 10
        dismiss = call_later_mock.call_args[0][2]
        notifications = persistent_notification._async_get_or_create_notifications(hass)
        assert notifications["ld2410_auto_sensitivities"]["message"] == (
            "Please keep the room empty for 10 seconds while calibration is in progress"
        )
        dismiss(None)
        notifications = persistent_notification._async_get_or_create_notifications(hass)
        assert "ld2410_auto_sensitivities" not in notifications


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_save_and_load_sensitivities_buttons(hass: HomeAssistant) -> None:
    """Test saving and loading sensitivities."""
    await async_setup_component(hass, DOMAIN, {})
    await async_setup_component(hass, "persistent_notification", {})
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
        "move_gate_sensitivity": list(range(9)),
        "still_gate_sensitivity": list(range(9, 18)),
    }
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
            AsyncMock(return_value=mock_parsed),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

    assert hass.states.get("button.test_name_save_sensitivities") is not None
    assert hass.states.get("button.test_name_load_sensitivities") is not None

    with (
        patch.object(hass.config_entries, "async_reload", AsyncMock()) as reload_mock,
        patch("custom_components.ld2410.button.async_call_later") as call_later_mock,
    ):
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.test_name_save_sensitivities"},
            blocking=True,
        )
        await hass.async_block_till_done()

    reload_mock.assert_not_called()

    assert (
        entry.options[CONF_SAVED_MOVE_SENSITIVITY]
        == mock_parsed["move_gate_sensitivity"]
    )
    assert (
        entry.options[CONF_SAVED_STILL_SENSITIVITY]
        == mock_parsed["still_gate_sensitivity"]
    )
    call_later_mock.assert_called_once()
    assert call_later_mock.call_args_list[0][0][1] == 10
    dismiss = call_later_mock.call_args_list[0][0][2]
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    assert notifications["ld2410_save_sensitivities"]["message"] == (
        "Sensitivities successfully saved to configurations"
    )
    dismiss(None)
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    assert "ld2410_save_sensitivities" not in notifications

    new_move = [50] * 9
    new_still = [60] * 9
    with patch.object(hass.config_entries, "async_reload", AsyncMock()):
        hass.config_entries.async_update_entry(
            entry,
            options={
                **entry.options,
                CONF_SAVED_MOVE_SENSITIVITY: new_move,
                CONF_SAVED_STILL_SENSITIVITY: new_still,
            },
        )

    with (
        patch(
            "custom_components.ld2410.api.LD2410.cmd_set_gate_sensitivity",
            AsyncMock(),
        ) as set_mock,
        patch("custom_components.ld2410.button.async_call_later") as call_later_mock,
    ):
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.test_name_load_sensitivities"},
            blocking=True,
        )
        await hass.async_block_till_done()

    set_mock.assert_has_awaits([call(g, 50, 60) for g in range(9)], any_order=False)
    call_later_mock.assert_called_once()
    assert call_later_mock.call_args_list[0][0][1] == 10
    dismiss = call_later_mock.call_args_list[0][0][2]
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    assert notifications["ld2410_load_sensitivities"]["message"] == (
        "Successfully loaded previously saved gate sensitivities into the device"
    )
    dismiss(None)
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    assert "ld2410_load_sensitivities" not in notifications
