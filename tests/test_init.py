from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.ld2410 import async_setup_entry, async_unload_entry
from custom_components.ld2410.const import DOMAIN


async def test_async_setup_entry(hass: HomeAssistant):
    """Test setting up a config entry."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test LD2410",
        data={"address": "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="test_unique_id",
        source="user",
        discovery_keys=set(),
    )

    hass.config_entries._entries[config_entry.entry_id] = config_entry

    with (
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address"
        ) as mock_ble_device,
        patch("custom_components.ld2410.get_device") as mock_get_device,
        patch("custom_components.ld2410.close_stale_connections_by_address"),
        patch("custom_components.ld2410.LD2410BLE") as mock_ld2410,
        patch("custom_components.ld2410.LD2410BLECoordinator") as mock_coord,
        patch(
            "homeassistant.components.bluetooth.async_register_callback",
            return_value=lambda *args, **kwargs: None,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"
        ) as mock_forward,
    ):
        mock_device = MagicMock()
        mock_device.address = "AA:BB:CC:DD:EE:FF"
        mock_ble_device.return_value = mock_device
        mock_get_device.return_value = mock_device

        ld_instance = MagicMock()
        ld_instance.initialise = AsyncMock()
        ld_instance.set_ble_device_and_advertisement_data = MagicMock()
        ld_instance.register_callback = MagicMock()
        ld_instance.register_disconnected_callback = MagicMock()
        ld_instance.stop = AsyncMock()
        mock_ld2410.return_value = ld_instance

        coord_instance = MagicMock()
        mock_coord.return_value = coord_instance

        mock_forward.return_value = True

        result = await async_setup_entry(hass, config_entry)
        assert result is True
        mock_ble_device.assert_called_once()
        mock_coord.assert_called_once()
        mock_forward.assert_called_once()


async def test_async_unload_entry(hass: HomeAssistant):
    """Test unloading a config entry."""
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test LD2410",
        data={"address": "AA:BB:CC:DD:EE:FF"},
        options={},
        entry_id="test_entry_id",
        unique_id="test_unique_id",
        source="user",
        discovery_keys=set(),
    )

    device = MagicMock()
    device.stop = AsyncMock()
    config_entry.runtime_data = MagicMock(device=device)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ) as mock_unload:
        result = await async_unload_entry(hass, config_entry)
        assert result is True
        mock_unload.assert_called_once()
        device.stop.assert_awaited_once()
