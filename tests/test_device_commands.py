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

from custom_components.ld2410.api.const import (
    CMD_BT_GET_PERMISSION,
    CMD_ENABLE_CFG,
    CMD_END_CFG,
    CMD_ENABLE_ENGINEERING,
)


def test_wrap_command_ack():
    """Ensure ACK command is wrapped correctly."""
    wrapped = _wrap_command("FF000100").hex()
    assert wrapped == "fdfcfbfa0400ff00010004030201"


def test_wrap_command_bt_password():
    """Ensure bluetooth password command is wrapped correctly."""
    key = CMD_BT_GET_PERMISSION + "".join(_password_to_words("HiLink"))
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
    assert await dev.cmd_send_bluetooth_password()
    assert dev.last_key == CMD_BT_GET_PERMISSION + "".join(_password_to_words("HiLink"))


@pytest.mark.asyncio
async def test_send_bluetooth_password_wrong_password() -> None:
    """Ensure a wrong password raises an error."""
    dev = _TestDevice(password="HiLink", response=b"\x01\x00")
    with pytest.raises(OperationError):
        await dev.cmd_send_bluetooth_password()


@pytest.mark.asyncio
async def test_enable_config_success() -> None:
    """Enable config command parses response."""
    dev = _TestDevice(password=None, response=b"\x00\x00\x01\x00\x00@")
    proto, buf = await dev.cmd_enable_config()
    assert (proto, buf) == (1, 16384)
    assert dev.last_key == CMD_ENABLE_CFG + "0001"


@pytest.mark.asyncio
async def test_enable_config_fail() -> None:
    """Enable config command raises on failure."""
    dev = _TestDevice(password=None, response=b"\x01\x00\x01\x00\x00@")
    with pytest.raises(OperationError):
        await dev.cmd_enable_config()


@pytest.mark.asyncio
async def test_end_config_success() -> None:
    """End config command sends correct key."""
    dev = _TestDevice(password=None, response=b"\x00\x00")
    await dev.cmd_end_config()
    assert dev.last_key == CMD_END_CFG


@pytest.mark.asyncio
async def test_end_config_fail() -> None:
    """End config command raises on failure."""
    dev = _TestDevice(password=None, response=b"\x01\x00")
    with pytest.raises(OperationError):
        await dev.cmd_end_config()


@pytest.mark.asyncio
async def test_enable_engineering_success() -> None:
    """Enable engineering command sends correct key."""
    dev = _TestDevice(password=None, response=b"\x00\x00")
    await dev.cmd_enable_engineering_mode()
    assert dev.last_key == CMD_ENABLE_ENGINEERING


@pytest.mark.asyncio
async def test_enable_engineering_fail() -> None:
    """Enable engineering command raises on failure."""
    dev = _TestDevice(password=None, response=b"\x01\x00")
    with pytest.raises(OperationError):
        await dev.cmd_enable_engineering_mode()


def test_unwrap_response():
    """Ensure responses are unwrapped correctly."""
    raw = bytes.fromhex("fdfcfbfa0400ff00010004030201")
    assert _unwrap_response(raw) == bytes.fromhex("ff000100")


def test_parse_response():
    """Ensure responses are parsed and ACK verified."""
    raw = bytes.fromhex("fdfcfbfa0400a801000004030201")
    assert _parse_response(CMD_BT_GET_PERMISSION, raw) == bytes.fromhex("0000")


@pytest.mark.parametrize("payload_hex", ["07", "09"])
def test_parse_response_rejects_short_payload(payload_hex: str) -> None:
    """Ensure single-byte payloads are rejected."""
    raw = bytes.fromhex(f"fdfcfbfa0100{payload_hex}04030201")
    with pytest.raises(OperationError):
        _parse_response(CMD_BT_GET_PERMISSION, raw)
