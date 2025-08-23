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
    """Inject a Bluetooth advertisement for tests.

    The real Home Assistant test helpers provide a rich Bluetooth testing
    harness. In this repository we only need a small subset of that
    behaviour. This helper stores the provided ``BluetoothServiceInfo`` in a
    lightweight manager and immediately notifies any registered callbacks.
    """
    from habluetooth.central_manager import get_manager, set_manager
    from homeassistant.components.bluetooth import BluetoothChange

    try:
        manager = get_manager()
    except RuntimeError:

        class _StubBluetoothManager:
            def __init__(self) -> None:
                self.service_info = {}
                self._callback = None

            def inject(self, service_info: BluetoothServiceInfo) -> None:
                self.service_info[service_info.address] = service_info
                if self._callback:
                    self._callback(service_info, BluetoothChange.ADVERTISEMENT)

            def async_address_present(self, address: str, connectable: bool) -> bool:
                return address in self.service_info

            def async_register_callback(self, callback, matcher) -> Callable[[], None]:
                self._callback = callback
                address = matcher.get("address") if matcher else None
                if address and address in self.service_info:
                    callback(self.service_info[address], BluetoothChange.ADVERTISEMENT)
                return lambda: None

            def async_track_unavailable(self, callback, address, connectable):
                return lambda: None

            def async_last_service_info(self, address: str, connectable: bool):
                return self.service_info.get(address)

        manager = _StubBluetoothManager()
        set_manager(manager)

    manager.inject(info)


async def get_diagnostics_for_config_entry(
    hass: HomeAssistant,
    hass_client: Callable[..., Coroutine[Any, Any, TestClient]],
    config_entry: ConfigEntry,
) -> dict[str, str]:
    """Return diagnostics for a config entry."""
    from custom_components.ld2410 import diagnostics as diag

    await hass.async_block_till_done()
    return await diag.async_get_config_entry_diagnostics(hass, config_entry)
