from typing import Any
from collections.abc import Callable, Coroutine
import inspect

from aiohttp.test_utils import TestClient
from bleak import AdvertisementData
from bleak.backends.device import BLEDevice
from habluetooth import BluetoothServiceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


class MockConfigEntry(ConfigEntry):
    """Mock config entry for testing."""

    def __init__(
        self,
        *,
        domain: str,
        data: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        entry_id: str | None = None,
        source: str = "user",
        title: str = "Mock Title",
        unique_id: str | None = None,
        version: int = 1,
        minor_version: int = 1,
        subentries_data: tuple[dict[str, Any], ...] | None = None,
    ) -> None:
        """Initialize a mock config entry."""
        kwargs = {
            "version": version,
            "minor_version": minor_version,
            "domain": domain,
            "title": title,
            "data": data or {},
            "options": options or {},
            "source": source,
            "entry_id": entry_id or "mock_entry_id",
            "unique_id": unique_id,
            "discovery_keys": {},
        }
        if "subentries_data" in inspect.signature(ConfigEntry.__init__).parameters:
            kwargs["subentries_data"] = subentries_data or ()
        super().__init__(**kwargs)

    def add_to_hass(self, hass: HomeAssistant) -> None:
        """Add this entry to Home Assistant."""
        hass.config_entries._entries[self.entry_id] = self


def generate_advertisement_data(
    local_name: str | None = None,
    manufacturer_data: dict[int, bytes] | None = None,
    service_data: dict[str, bytes] | None = None,
    service_uuids: list[str] | None = None,
    tx_power: int | None = None,
    rssi: int = -60,
):
    """Generate advertisement data for testing."""
    return AdvertisementData(
        local_name=local_name,
        manufacturer_data=manufacturer_data or {},
        service_data=service_data or {},
        service_uuids=service_uuids or [],
        tx_power=tx_power,
        rssi=rssi,
        platform_data=(),
    )


def generate_ble_device(
    address: str,
    name: str | None = None,
) -> BLEDevice:
    """Generate a BLE device for testing."""
    return BLEDevice(
        address=address,
        name=name,
        details={},
    )


def inject_bluetooth_service_info(
    hass: HomeAssistant, info: BluetoothServiceInfo
) -> None:
    """mock injection of service info."""
    return


async def get_diagnostics_for_config_entry(
    hass: HomeAssistant,
    hass_client: Callable[..., Coroutine[Any, Any, TestClient]],
    config_entry: ConfigEntry,
) -> dict[str, str]:
    """Return the diagnostics config entry for the specified domain."""
    return {}
