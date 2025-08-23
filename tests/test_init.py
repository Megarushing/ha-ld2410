"""Test the ld2410 init."""

from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import pytest

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


@pytest.mark.parametrize(
    ("exception", "error_message"),
    [
        (
            ValueError("wrong model"),
            "LD2410 device initialization failed because of incorrect configuration parameters: wrong model",
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
        "custom_components.ld2410.api.ld2410.LD2410Device.__init__",
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
        patch("custom_components.ld2410.api.ld2410.close_stale_connections_by_address"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert "Could not find LD2410 test with address AA:BB:CC:DD:EE:FF" in caplog.text


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
        patch("custom_components.ld2410.api.ld2410.close_stale_connections_by_address"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert "AA:BB:CC:DD:EE:FF is not advertising state" in caplog.text
