"""Define fixtures available for all tests."""

import pytest
from bleak.backends.device import BLEDevice

from custom_components.ld2410.const import (
    DOMAIN,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME, CONF_SENSOR_TYPE

try:
    from tests.common import MockConfigEntry
except ImportError:
    from .mocks import MockConfigEntry


# Make HA load integrations from ./custom_components/*
@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    yield


# If present, this already prevents real BLE scanning; harmless if not.
@pytest.fixture(autouse=True)
def _mock_bt(mock_bluetooth):
    yield


@pytest.fixture(autouse=True)
def _patch_ble_device_from_address(monkeypatch):
    def _fake(hass, address, connectable=True):
        # Create a minimal BLEDevice that matches your entry’s address
        return BLEDevice(address=address, name="HLK-LD2410", details=None, rssi=-60)

    monkeypatch.setattr(
        "homeassistant.components.bluetooth.async_ble_device_from_address",
        _fake,
        raising=False,
    )
    yield


@pytest.fixture(autouse=True)
def _mac_safe_bluetooth(monkeypatch):
    async def _ok(*args, **kwargs):
        return True

    # 1) Short-circuit setup for both deps so HA is satisfied but does nothing
    monkeypatch.setattr(
        "homeassistant.components.bluetooth.async_setup", _ok, raising=False
    )
    monkeypatch.setattr(
        "homeassistant.components.bluetooth.async_setup_entry", _ok, raising=False
    )
    monkeypatch.setattr(
        "homeassistant.components.bluetooth_adapters.async_setup", _ok, raising=False
    )
    monkeypatch.setattr(
        "homeassistant.components.bluetooth_adapters.async_setup_entry",
        _ok,
        raising=False,
    )

    # 2) Replace the BluetoothManager *symbol* everywhere HA might import it
    class _FakeBTManager:
        def __init__(self, *a, **kw):
            self._all_history = {}
            self._connectable_history = {}
            self.storage = None

        async def async_setup(self):
            return

        async def async_stop(self):
            return

        # Optional API, present just in case something queries it
        def async_get_scanner(self):
            return None

    # Patch in all likely import locations (don’t modify the immutable class, replace the reference)
    monkeypatch.setattr(
        "homeassistant.components.bluetooth.BluetoothManager",
        _FakeBTManager,
        raising=False,
    )
    monkeypatch.setattr(
        "homeassistant.components.bluetooth.manager.BluetoothManager",
        _FakeBTManager,
        raising=False,
    )
    monkeypatch.setattr(
        "habluetooth.manager.BluetoothManager", _FakeBTManager, raising=False
    )

    # 3) Ensure any history loader path is a no-op, no matter where referenced
    def _fake_history(_adapters, _storage):
        return {}, {}

    monkeypatch.setattr(
        "homeassistant.components.bluetooth.manager.async_load_history_from_system",
        _fake_history,
        raising=False,
    )
    monkeypatch.setattr(
        "homeassistant.components.bluetooth.util.async_load_history_from_system",
        _fake_history,
        raising=False,
    )

    # Safety net: if bluetooth_adapters.dbus is imported, make unpack a pass-through
    try:
        import bluetooth_adapters.dbus as _dbus  # type: ignore

        monkeypatch.setattr(_dbus, "unpack_variants", lambda x: x, raising=False)
    except Exception:
        pass


@pytest.fixture
def entity_registry_enabled_by_default():
    """Fixture for compatibility with Home Assistant tests."""
    return True


@pytest.fixture
def mock_entry_factory():
    """Fixture to create a MockConfigEntry with a customizable sensor type."""
    return lambda sensor_type="ld2410": MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_SENSOR_TYPE: sensor_type,
        },
        unique_id="aabbccddeeff",
    )
