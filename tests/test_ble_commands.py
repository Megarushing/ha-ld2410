from unittest.mock import patch

import pytest
from bleak.backends.device import BLEDevice
from homeassistant.core import HomeAssistant

from custom_components.ld2410.api.ld2410.devices.device import LD2410Device
from custom_components.ld2410.api.ld2410.const import (
    CHARACTERISTIC_NOTIFY,
    CHARACTERISTIC_WRITE,
    CMD_BT_PASS_POST,
    CMD_BT_PASS_PRE,
    CMD_DISABLE_CONFIG,
    CMD_ENABLE_CONFIG,
    CMD_ENABLE_ENGINEERING_MODE,
)


class MockCharacteristic:
    def __init__(self, uuid: str) -> None:
        self.uuid = uuid


class MockServices:
    def get_characteristic(self, uuid):  # type: ignore[override]
        return MockCharacteristic(str(uuid))


class MockClient:
    def __init__(self) -> None:
        self.is_connected = True
        self.services = MockServices()
        self.write_calls: list[tuple[str, bytes]] = []
        self.notify_calls: list[str] = []

    async def write_gatt_char(self, char, data, response):
        self.write_calls.append((char.uuid, data))

    async def start_notify(self, char, callback):
        self.notify_calls.append(char.uuid)

    async def disconnect(self):
        return


@pytest.mark.asyncio
async def test_initialise_sends_commands_using_correct_characteristics(
    hass: HomeAssistant,
) -> None:
    ble_device = BLEDevice("AA:BB:CC:DD:EE:FF", "test", {})
    client = MockClient()

    async def mock_ensure_connected(self):
        self._client = client
        self._read_char = MockCharacteristic(CHARACTERISTIC_NOTIFY)
        self._write_char = MockCharacteristic(CHARACTERISTIC_WRITE)

    with patch(
        "custom_components.ld2410.api.ld2410.devices.device.LD2410BaseDevice._ensure_connected",
        mock_ensure_connected,
    ):
        device = LD2410Device(device=ble_device, password="HiLink")
        await device.initialise()
        await device._execute_disconnect()

    expected_first = CMD_BT_PASS_PRE + b"HiLink" + CMD_BT_PASS_POST
    assert client.notify_calls[0] == CHARACTERISTIC_NOTIFY
    assert client.write_calls == [
        (CHARACTERISTIC_WRITE, expected_first),
        (CHARACTERISTIC_WRITE, CMD_ENABLE_CONFIG),
        (CHARACTERISTIC_WRITE, CMD_ENABLE_ENGINEERING_MODE),
        (CHARACTERISTIC_WRITE, CMD_DISABLE_CONFIG),
    ]


@pytest.mark.asyncio
async def test_notification_callback_logs_stream(hass: HomeAssistant) -> None:
    ble_device = BLEDevice("AA:BB:CC:DD:EE:FF", "test", {})
    client = MockClient()

    async def mock_ensure_connected(self):
        self._client = client
        self._read_char = MockCharacteristic(CHARACTERISTIC_NOTIFY)
        self._write_char = MockCharacteristic(CHARACTERISTIC_WRITE)

    with patch(
        "custom_components.ld2410.api.ld2410.devices.device.LD2410BaseDevice._ensure_connected",
        mock_ensure_connected,
    ):
        device = LD2410Device(device=ble_device, password="HiLink")
        records: list[bytearray] = []
        device.subscribe_data_stream(lambda data: records.append(data))
        await device.initialise()
        device._notification_handler(0, b"abc")

    assert records == [b"abc"]
