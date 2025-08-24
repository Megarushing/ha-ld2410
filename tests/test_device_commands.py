from bleak.backends.device import BLEDevice
import pytest

from custom_components.ld2410.api.devices.device import (
    _password_to_words,
    _unwrap_response,
    _wrap_command,
    _parse_response,
    BaseDevice,
)
from custom_components.ld2410.api.const import CMD_BT_PASSWORD


def test_wrap_command_ack():
    """Ensure ACK command is wrapped correctly."""
    wrapped = _wrap_command("FF000100").hex()
    assert wrapped == "fdfcfbfa0400ff00010004030201"


def test_wrap_command_bt_password():
    """Ensure bluetooth password command is wrapped correctly."""
    key = CMD_BT_PASSWORD + "".join(_password_to_words("HiLink"))
    wrapped = _wrap_command(key).hex()
    assert wrapped == "fdfcfbfa0800a80048694c696e6b04030201"


class _TestDevice(BaseDevice):
    def __init__(self, password: str | None) -> None:
        super().__init__(
            device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
            password=password,
        )

    async def _send_command(self, key: str, retry: int | None = None) -> bytes | None:
        self.last_key = key
        return b""


@pytest.mark.asyncio
async def test_send_bluetooth_password_uses_config_password() -> None:
    """Ensure the device uses the configured password when none provided."""
    dev = _TestDevice(password="HiLink")
    await dev.send_bluetooth_password()
    assert dev.last_key == CMD_BT_PASSWORD + "".join(_password_to_words("HiLink"))


def test_unwrap_response():
    """Ensure responses are unwrapped correctly."""
    raw = bytes.fromhex("fdfcfbfa0400ff00010004030201")
    assert _unwrap_response(raw) == bytes.fromhex("ff000100")


def test_parse_response():
    """Ensure responses are parsed and ACK verified."""
    raw = bytes.fromhex("fdfcfbfa0400a801000004030201")
    assert _parse_response(CMD_BT_PASSWORD, raw) == bytes.fromhex("0000")
