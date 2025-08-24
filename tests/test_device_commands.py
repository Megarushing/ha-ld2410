from bleak.backends.device import BLEDevice
import pytest

from custom_components.ld2410.api.devices.device import (
    _password_to_words,
    _unwrap_response,
    _wrap_command,
    _parse_response,
    OperationError,
)
from custom_components.ld2410.api.devices.ld2410 import LD2410
import logging

from custom_components.ld2410.api.const import (
    CMD_BT_PASSWORD,
    DEVICE_CMD_HEADER,
    DEVICE_CMD_FOOTER,
)


def test_wrap_command_ack():
    """Ensure ACK command is wrapped correctly."""
    wrapped = _wrap_command("FF000100").hex()
    assert wrapped == "fdfcfbfa0400ff00010004030201"


def test_wrap_command_bt_password():
    """Ensure bluetooth password command is wrapped correctly."""
    key = CMD_BT_PASSWORD + "".join(_password_to_words("HiLink"))
    wrapped = _wrap_command(key).hex()
    assert wrapped == "fdfcfbfa0800a80048694c696e6b04030201"


class _TestDevice(LD2410):
    def __init__(self, password: str | None, response: bytes = b"\x00\x00") -> None:
        super().__init__(
            device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
            password=password,
        )
        self._response = response

    async def _send_command(self, key: str, retry: int | None = None) -> bytes | None:
        self.last_key = key
        return self._response


@pytest.mark.asyncio
async def test_send_bluetooth_password_uses_config_password() -> None:
    """Ensure the device uses the configured password when none provided."""
    dev = _TestDevice(password="HiLink")
    await dev.cmd_send_bluetooth_password()
    assert dev.last_key == CMD_BT_PASSWORD + "".join(_password_to_words("HiLink"))


@pytest.mark.asyncio
async def test_send_bluetooth_password_wrong_password() -> None:
    """Ensure a wrong password raises an error."""
    dev = _TestDevice(password="HiLink", response=b"\x01\x00")
    with pytest.raises(OperationError):
        await dev.cmd_send_bluetooth_password()


def test_unwrap_response():
    """Ensure responses are unwrapped correctly."""
    raw = bytes.fromhex("fdfcfbfa0400ff00010004030201")
    assert _unwrap_response(raw) == bytes.fromhex("ff000100")


def test_parse_response():
    """Ensure responses are parsed and ACK verified."""
    raw = bytes.fromhex("fdfcfbfa0400a801000004030201")
    assert _parse_response(CMD_BT_PASSWORD, raw) == bytes.fromhex("0000")


@pytest.mark.parametrize("payload_hex", ["07", "09"])
def test_parse_response_rejects_short_payload(payload_hex: str) -> None:
    """Ensure single-byte payloads are rejected."""
    raw = bytes.fromhex(f"fdfcfbfa0100{payload_hex}04030201")
    with pytest.raises(OperationError):
        _parse_response(CMD_BT_PASSWORD, raw)


def test_device_command_notification(caplog) -> None:
    """Ensure device command frames are logged separately."""
    dev = _TestDevice(password="HiLink")
    dev._notify_future = dev.loop.create_future()
    caplog.set_level(logging.DEBUG)
    frame_hex = DEVICE_CMD_HEADER + "0400a1000203" + DEVICE_CMD_FOOTER
    dev._notification_handler(0, bytearray.fromhex(frame_hex))
    assert not dev._notify_future.done()
    assert any(
        "Received device command: a100 params: 0203" in record.getMessage()
        for record in caplog.records
    )
