"""Test component setup."""

from unittest.mock import AsyncMock, patch, MagicMock
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.ld2410 import async_setup_entry, async_unload_entry
from custom_components.ld2410.const import DOMAIN


async def test_async_setup_entry(hass: HomeAssistant):
    """Test setting up a config entry."""
    # Create a mock config entry
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test LD2410",
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "sensor_type": "ld2410",
        },
        options={"retry_count": 3},
        entry_id="test_entry_id",
        unique_id="test_unique_id",
        source="user",
        discovery_keys=set(),
    )

    # Add the config entry to the hass registry
    hass.config_entries._entries[config_entry.entry_id] = config_entry

    # Mock all the Bluetooth and device dependencies
    with (
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address"
        ) as mock_ble_device,
        patch("custom_components.ld2410.api.ld2410.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.LD2410DataUpdateCoordinator"
        ) as mock_coordinator,
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"
        ) as mock_forward,
    ):
        # Mock a BLE device
        mock_device = MagicMock()
        mock_device.address = "AA:BB:CC:DD:EE:FF"
        mock_ble_device.return_value = mock_device

        # Mock coordinator with proper async return values
        mock_coord_instance = MagicMock()
        # Mock async_start to return a callable that can be used with async_on_unload
        mock_coord_instance.async_start = MagicMock(return_value=lambda: None)
        # Mock async_wait_ready as an async function returning True
        mock_coord_instance.async_wait_ready = AsyncMock(return_value=True)
        mock_coordinator.return_value = mock_coord_instance

        # Mock platform forward setup
        mock_forward.return_value = True

        # Test setup
        result = await async_setup_entry(hass, config_entry)
        assert result is True

        # Verify calls were made
        mock_ble_device.assert_called_once()
        assert mock_ble_device.call_args.args[2] is True
        mock_coordinator.assert_called_once()
        mock_forward.assert_called_once()


async def test_async_unload_entry(hass: HomeAssistant):
    """Test unloading a config entry."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test LD2410",
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "sensor_type": "ld2410",
        },
        options={"retry_count": 3},
        entry_id="test_entry_id",
        unique_id="test_unique_id",
        source="user",
        discovery_keys=set(),
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms"
    ) as mock_unload:
        mock_unload.return_value = True

        result = await async_unload_entry(hass, config_entry)
        assert result is True
        mock_unload.assert_called_once()
