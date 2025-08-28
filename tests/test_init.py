"""Test the integration init."""

from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import (
    CONF_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSOR_TYPE,
)
from homeassistant.core import HomeAssistant

from . import (
    LD2410b_SERVICE_INFO,
    patch_async_ble_device_from_address,
)

try:
    from tests.common import MockConfigEntry
except ImportError:
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import inject_bluetooth_service_info
except ImportError:
    from .mocks import inject_bluetooth_service_info

from custom_components.ld2410.const import DOMAIN


@pytest.mark.parametrize(
    ("exception", "error_message"),
    [
        (
            ValueError("wrong model"),
            "Device initialization failed because of incorrect configuration parameters: wrong model",
        ),
    ],
)
async def test_exception_handling_for_device_initialization(
    hass: HomeAssistant,
    mock_entry_factory: Callable[[str], MockConfigEntry],
    exception: Exception,
    error_message: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test exception handling for lock initialization."""
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = mock_entry_factory("somethingelse")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ld2410.api.Device.__init__",
        side_effect=exception,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert error_message in caplog.text


async def test_setup_entry_without_ble_device(
    hass: HomeAssistant,
    mock_entry_factory: Callable[[str], MockConfigEntry],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test setup entry without ble device."""

    entry = mock_entry_factory("test")
    entry.add_to_hass(hass)

    with (
        patch_async_ble_device_from_address(None),
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert "Could not find test with address AA:BB:CC:DD:EE:FF" in caplog.text


async def test_coordinator_wait_ready_timeout(
    hass: HomeAssistant,
    mock_entry_factory: Callable[[str], MockConfigEntry],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the coordinator async_wait_ready timeout by calling it directly."""

    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = mock_entry_factory("ld2410")
    entry.add_to_hass(hass)

    timeout_mock = AsyncMock()
    timeout_mock.__aenter__.side_effect = TimeoutError
    timeout_mock.__aexit__.return_value = None

    with (
        patch(
            "custom_components.ld2410.coordinator.asyncio.timeout",
            return_value=timeout_mock,
        ),
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert "AA:BB:CC:DD:EE:FF is not advertising state" in caplog.text


async def test_send_password_on_setup(hass: HomeAssistant) -> None:
    """Ensure the bluetooth password is sent during setup."""
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "abc123",
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
        ) as mock_send,
        patch(
            "custom_components.ld2410.api.devices.device.Device._ensure_connected",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_config",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_engineering_mode",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_end_config",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_read_params",
            AsyncMock(
                return_value={
                    "move_gate_sensitivity": [],
                    "still_gate_sensitivity": [],
                    "absence_delay": 0,
                }
            ),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._update_parsed_data",
            autospec=True,
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mock_send.assert_awaited_once()


async def test_unload_disconnects_device(hass: HomeAssistant) -> None:
    """Ensure unloading disconnects the device and stops notifications."""
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
            "custom_components.ld2410.api.devices.device.Device._ensure_connected",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_config",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_engineering_mode",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_end_config",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_read_params",
            AsyncMock(
                return_value={
                    "move_gate_sensitivity": [],
                    "still_gate_sensitivity": [],
                    "absence_delay": 0,
                }
            ),
        ),
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._update_parsed_data",
            autospec=True,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    device = entry.runtime_data.device
    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_char = object()
    device._client = mock_client
    device._read_char = mock_char

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    mock_client.stop_notify.assert_awaited_once_with(mock_char)
    mock_client.disconnect.assert_awaited_once()
