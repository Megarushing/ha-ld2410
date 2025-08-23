"""Tests for the ld2410 integration."""

from unittest.mock import patch

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from contextlib import contextmanager

# Import test utilities from Home Assistant
try:
    from tests.common import MockConfigEntry
except ImportError:
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import (
        generate_advertisement_data,
        generate_ble_device,
    )
except ImportError:
    from .mocks import (
        generate_advertisement_data,
        generate_ble_device,
    )

DOMAIN = "ld2410"

ENTRY_CONFIG = {
    CONF_ADDRESS: "e7:89:43:99:99:99",
}

USER_INPUT = {
    CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
}

USER_INPUT_UNSUPPORTED_DEVICE = {
    CONF_ADDRESS: "test",
}

USER_INPUT_INVALID = {
    CONF_ADDRESS: "invalid-mac",
}

@contextmanager
def patch_async_setup_entry(domain="ld2410"):
    with patch(f"custom_components.{domain}.async_setup_entry", return_value=True) as m:
        yield m

@contextmanager
def patch_async_setup(domain="ld2410"):
    with patch(f"custom_components.{domain}.async_setup", return_value=True) as m:
        yield m


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

NOT_LD2410_INFO = BluetoothServiceInfoBleak(
    name="unknown",
    service_uuids=[],
    address="aa:bb:cc:dd:ee:ff",
    manufacturer_data={},
    service_data={},
    rssi=-60,
    source="local",
    advertisement=generate_advertisement_data(
        manufacturer_data={},
        service_data={},
    ),
    device=generate_ble_device("aa:bb:cc:dd:ee:ff", "unknown"),
    time=0,
    connectable=True,
    tx_power=-127,
)

LD2410b_NOT_CONNECTABLE = BluetoothServiceInfoBleak(
    name = "HLK-LD2410_96D8",
    manufacturer_data = {
        256: b'D\x02\x101\x07$\x00\xaa\xbb\xcc\xdd\xee\xff',
        1494: b"\x08\x00JLAISDK",
    },
    service_data = {},
    service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    address = "AA:BB:CC:DD:EE:FF",
    rssi = -90,
    source = "local",
    advertisement = generate_advertisement_data(
        local_name="HLK-LD2410_96D8",
        manufacturer_data={
            256: b'D\x02\x101\x07$\x00\xaa\xbb\xcc\xdd\xee\xff',
            1494: b"\x08\x00JLAISDK",
        },
        service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"]
    ),
    device = generate_ble_device("AA:BB:CC:DD:EE:FF", "HLK-LD2410_96D8"),
    time = 0,
    connectable = False,
    tx_power = -127,
)

LD2410b_SERVICE_INFO = BluetoothServiceInfoBleak(
    name = "HLK-LD2410_96D8",
    manufacturer_data = {
        256: b"D\x02\x101\x07$\x00Bl\x99O\x96\xd8",
        1494: b"\x08\x00JLAISDK",
    },
    service_data = {},
    service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    address = "AA:BB:CC:DD:EE:FF",
    rssi = -90,
    source = "local",
    advertisement = generate_advertisement_data(
        local_name="HLK-LD2410_96D8",
        manufacturer_data={
            256: b"D\x02\x101\x07$\x00Bl\x99O\x96\xd8",
            1494: b"\x08\x00JLAISDK",
        },
        service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"]
    ),
    device = generate_ble_device("AA:BB:CC:DD:EE:FF", "HLK-LD2410_96D8"),
    time = 0,
    connectable = True,
    tx_power = -127,
)

LD2410b_2_SERVICE_INFO = BluetoothServiceInfoBleak(
    name = "HLK-LD2410_DADB",
    manufacturer_data = {
        256: b"D\x02\x101\x07$\x00O\x06O\xc1\xda\xdb",
        1494: b"\x08\x00JLAISDK",
    },
    service_data = {},
    service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"],
    address = "4F:06:4F:C1:DA:DB",
    rssi = -90,
    source = "local",
    advertisement = generate_advertisement_data(
        local_name="HLK-LD2410_DADB",
        manufacturer_data={
            256: b"D\x02\x101\x07$\x00O\x06O\xc1\xda\xdb",
            1494: b"\x08\x00JLAISDK",
        },
        service_uuids=["0000af30-0000-1000-8000-00805f9b34fb"]
    ),
    device = generate_ble_device("4F:06:4F:C1:DA:DB", "HLK-LD2410_DADB"),
    time = 0,
    connectable = True,
    tx_power = -127,
)
