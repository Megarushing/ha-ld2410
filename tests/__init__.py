"""Tests for the ld2410 integration."""

from unittest.mock import patch

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

# Import test utilities from Home Assistant
try:
    from tests.common import MockConfigEntry
except ImportError:
    from homeassistant.config_entries import ConfigEntry
    from typing import Any
    
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
                "discovery_keys": {},  # Required for newer HA versions
                "subentries_data": {},  # Required for newer HA versions
            }
            super().__init__(**kwargs)
        
        def add_to_hass(self, hass: HomeAssistant) -> None:
            """Add this entry to Home Assistant."""
            hass.config_entries._entries[self.entry_id] = self

try:
    from tests.components.bluetooth import generate_advertisement_data, generate_ble_device
except ImportError:
    from bleak.backends.device import BLEDevice
    from bleak import AdvertisementData
    
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

DOMAIN = "ld2410"

ENTRY_CONFIG = {
    CONF_ADDRESS: "e7:89:43:99:99:99",
}

USER_INPUT = {
    CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
}

USER_INPUT_UNSUPPORTED_DEVICE = {
    CONF_ADDRESS: "test",
}

USER_INPUT_INVALID = {
    CONF_ADDRESS: "invalid-mac",
}


def patch_async_setup_entry(return_value=True):
    """Patch async setup entry to return True."""
    return patch(
        f"homeassistant.components.{DOMAIN}.async_setup_entry",
        return_value=return_value,
    )


async def init_integration(hass: HomeAssistant) -> MockConfigEntry:
    """Set up the LD2410 integration in Home Assistant."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_CONFIG)
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    return entry


def patch_async_ble_device_from_address(return_value: BluetoothServiceInfoBleak | None):
    """Patch async ble device from address to return a given value."""
    return patch(
        "homeassistant.components.bluetooth.async_ble_device_from_address",
        return_value=return_value,
    )


# LD2410-specific test service info
LD2410_SERVICE_INFO = BluetoothServiceInfoBleak(
    name="HLK-LD2410B_123",
    manufacturer_data={256: b"\x07\x01\x00\x00\x00\x00\x00\x00"},
    service_data={"0000af30-0000-1000-8000-00805f9b34fb": b"\x01\x02\x03\x04"},
    service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    address="AA:BB:CC:DD:EE:FF",
    rssi=-60,
    source="local",
    advertisement=generate_advertisement_data(
        local_name="HLK-LD2410B_123",
        manufacturer_data={256: b"\x07\x01\x00\x00\x00\x00\x00\x00"},
        service_data={"0000af30-0000-1000-8000-00805f9b34fb": b"\x01\x02\x03\x04"},
        service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    ),
    device=generate_ble_device("AA:BB:CC:DD:EE:FF", "HLK-LD2410B_123"),
    time=0,
    connectable=True,
    tx_power=-60,
)

LD2410_MOTION_SENSOR_INFO = BluetoothServiceInfoBleak(
    name="HLK-LD2410_Motion",
    manufacturer_data={256: b"\x07\x01\x01\x00\x00\x00\x00\x00"},
    service_data={"0000af30-0000-1000-8000-00805f9b34fb": b"\x02\x03\x04\x05"},
    service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    address="BB:CC:DD:EE:FF:AA",
    rssi=-65,
    source="local",
    advertisement=generate_advertisement_data(
        local_name="HLK-LD2410_Motion",
        manufacturer_data={256: b"\x07\x01\x01\x00\x00\x00\x00\x00"},
        service_data={"0000af30-0000-1000-8000-00805f9b34fb": b"\x02\x03\x04\x05"},
        service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    ),
    device=generate_ble_device("BB:CC:DD:EE:FF:AA", "HLK-LD2410_Motion"),
    time=0,
    connectable=False,
    tx_power=-65,
)

LD2410_CONTACT_SENSOR_INFO = BluetoothServiceInfoBleak(
    name="HLK-LD2410_Contact",
    manufacturer_data={256: b"\x07\x01\x02\x00\x00\x00\x00\x00"},
    service_data={"0000af30-0000-1000-8000-00805f9b34fb": b"\x03\x04\x05\x06"},
    service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    address="CC:DD:EE:FF:AA:BB",
    rssi=-70,
    source="local",
    advertisement=generate_advertisement_data(
        local_name="HLK-LD2410_Contact",
        manufacturer_data={256: b"\x07\x01\x02\x00\x00\x00\x00\x00"},
        service_data={"0000af30-0000-1000-8000-00805f9b34fb": b"\x03\x04\x05\x06"},
        service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    ),
    device=generate_ble_device("CC:DD:EE:FF:AA:BB", "HLK-LD2410_Contact"),
    time=0,
    connectable=False,
    tx_power=-70,
)

NOT_LD2410_INFO = BluetoothServiceInfoBleak(
    name="unknown",
    service_uuids=[],
    address="dd:ee:ff:aa:bb:cc",
    manufacturer_data={},
    service_data={},
    rssi=-60,
    source="local",
    advertisement=generate_advertisement_data(
        manufacturer_data={},
        service_data={},
    ),
    device=generate_ble_device("dd:ee:ff:aa:bb:cc", "unknown"),
    time=0,
    connectable=True,
    tx_power=-127,
)
