from bleak.backends.device import BLEDevice
import pytest
from unittest.mock import AsyncMock

from custom_components.ld2410.api.devices.device import OperationError
from custom_components.ld2410.api.devices.ld2410 import (
    LD2410,
    _password_to_words,
    _unwrap_frame,
)

from custom_components.ld2410.api.const import (
    CMD_BT_GET_PERMISSION,
    CMD_ENABLE_CFG,
    CMD_END_CFG,
    CMD_ENABLE_ENGINEERING,
    CMD_START_AUTO_THRESH,
    CMD_QUERY_AUTO_THRESH,
    CMD_SET_MAX_GATES_AND_NOBODY,
    CMD_SET_SENSITIVITY,
    CMD_READ_PARAMS,
    CMD_REBOOT,
    CMD_SET_RES,
    CMD_GET_RES,
    CMD_GET_AUX,
    PAR_MAX_MOVE_GATE,
    PAR_MAX_STILL_GATE,
    PAR_NOBODY_DURATION,
    TX_HEADER,
    TX_FOOTER,
)


def test_modify_command_ack():
    """Ensure ACK command is modified correctly."""
    dev = _TestDevice(password=None)
    wrapped = dev._modify_command("FF000100").hex()
    assert wrapped == "fdfcfbfa0400ff00010004030201"


def test_modify_command_bt_password():
    """Ensure bluetooth password command is modified correctly."""
    key = CMD_BT_GET_PERMISSION + "".join(_password_to_words("HiLink"))
    dev = _TestDevice(password=None)
    wrapped = dev._modify_command(key).hex()
    assert wrapped == "fdfcfbfa0800a80048694c696e6b04030201"


class _TestDevice(LD2410):
    def __init__(
        self, password: str | None, response: bytes | list[bytes] = b"\x00\x00"
    ) -> None:
        super().__init__(
            device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
            password=password,
        )
        self._response = response
        self.keys: list[str] = []

    async def _send_command(
        self, key: str, retry: int | None = None, *, wait_for_response: bool = True
    ) -> bytes | None:
        self.last_key = key
        self.keys.append(key)
        if isinstance(self._response, list):
            return self._response.pop(0)
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
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00",
            b"\x00\x00",
        ],
    )
    await dev.cmd_enable_engineering_mode()
    assert dev.keys == [
        CMD_ENABLE_CFG + "0001",
        CMD_ENABLE_ENGINEERING,
        CMD_END_CFG,
    ]


@pytest.mark.asyncio
async def test_enable_engineering_fail() -> None:
    """Enable engineering command raises on failure."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x01\x00",
            b"\x00\x00",
        ],
    )
    with pytest.raises(OperationError):
        await dev.cmd_enable_engineering_mode()
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_ENABLE_ENGINEERING]


@pytest.mark.asyncio
async def test_auto_thresholds_success() -> None:
    """Auto thresholds command sends correct key."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00",
            b"\x00\x00",
        ],
    )
    await dev.cmd_auto_thresholds(5)
    assert dev.keys == [
        CMD_ENABLE_CFG + "0001",
        CMD_START_AUTO_THRESH + "0500",
        CMD_END_CFG,
    ]


@pytest.mark.asyncio
async def test_auto_thresholds_fail() -> None:
    """Auto thresholds command raises on failure."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x01\x00",
            b"\x00\x00",
        ],
    )
    with pytest.raises(OperationError):
        await dev.cmd_auto_thresholds(5)
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_START_AUTO_THRESH + "0500"]


@pytest.mark.asyncio
async def test_query_auto_thresholds_success() -> None:
    """Query auto thresholds command parses response."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00\x02\x00",
            b"\x00\x00",
        ],
    )
    status = await dev.cmd_query_auto_thresholds()
    assert status == 2
    assert dev.keys == [
        CMD_ENABLE_CFG + "0001",
        CMD_QUERY_AUTO_THRESH,
        CMD_END_CFG,
    ]


@pytest.mark.asyncio
async def test_query_auto_thresholds_fail() -> None:
    """Query auto thresholds command raises on failure."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00\x01",
            b"\x00\x00",
        ],
    )
    with pytest.raises(OperationError):
        await dev.cmd_query_auto_thresholds()
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_QUERY_AUTO_THRESH]


@pytest.mark.asyncio
async def test_set_gate_sensitivity_success() -> None:
    """Set gate sensitivity command sends correct key and updates cache."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00",
            b"\x00\x00",
        ],
    )
    dev._update_parsed_data(
        {
            "move_gate_sensitivity": [0] * 9,
            "still_gate_sensitivity": [0] * 9,
        }
    )
    await dev.cmd_set_gate_sensitivity(4, 15, 40)
    assert dev.keys == [
        CMD_ENABLE_CFG + "0001",
        CMD_SET_SENSITIVITY + "00000400000001000f000000020028000000",
        CMD_END_CFG,
    ]
    assert dev.parsed_data["move_gate_sensitivity"][4] == 15
    assert dev.parsed_data["still_gate_sensitivity"][4] == 40


@pytest.mark.asyncio
async def test_set_gate_sensitivity_fail() -> None:
    """Set gate sensitivity command raises on failure."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x01\x00",
            b"\x00\x00",
        ],
    )
    dev._update_parsed_data(
        {
            "move_gate_sensitivity": [0] * 9,
            "still_gate_sensitivity": [0] * 9,
        }
    )
    with pytest.raises(OperationError):
        await dev.cmd_set_gate_sensitivity(4, 15, 40)
    assert dev.keys == [
        CMD_ENABLE_CFG + "0001",
        CMD_SET_SENSITIVITY + "00000400000001000f000000020028000000",
    ]


@pytest.mark.asyncio
async def test_read_params_success() -> None:
    """Read parameters command parses response."""
    resp = [
        b"\x00\x00\x01\x00\x00@",
        b"\x00\x00"
        + bytes.fromhex("aa080507")
        + b"\x01" * 9
        + b"\x02" * 9
        + b"\x1e\x00",
        b"\x00\x00",
    ]
    dev = _TestDevice(password=None, response=resp)
    params = await dev.cmd_read_params()
    assert params == {
        "max_gate": 8,
        "max_move_gate": 5,
        "max_still_gate": 7,
        "move_gate_sensitivity": [1] * 9,
        "still_gate_sensitivity": [2] * 9,
        "absence_delay": 30,
    }
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_READ_PARAMS, CMD_END_CFG]


@pytest.mark.asyncio
async def test_read_params_fail() -> None:
    """Read parameters command raises on failure."""
    resp = [
        b"\x00\x00\x01\x00\x00@",
        b"\x00\x00\xaa\x08\x05",
        b"\x00\x00",
    ]
    dev = _TestDevice(password=None, response=resp)
    with pytest.raises(OperationError):
        await dev.cmd_read_params()
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_READ_PARAMS]


@pytest.mark.asyncio
async def test_initial_setup_reads_params() -> None:
    """initial_setup reads parameters and stores them."""
    resp = [
        b"\x00\x00\x01\x00\x00@",
        b"\x00\x00",
        b"\x00\x00",
        b"\x00\x00\x01\x00\x00@",
        b"\x00\x00"
        + bytes.fromhex("aa080507")
        + b"\x01" * 9
        + b"\x02" * 9
        + b"\x1e\x00",
        b"\x00\x00",
        b"\x00\x00\x01\x00\x00@",
        b"\x00\x00\x00\x00",
        b"\x00\x00",
        b"\x00\x00\x01\x00\x00@",
        b"\x00\x00\x01\x64\x00\x00",
        b"\x00\x00",
    ]
    dev = _TestDevice(password=None, response=resp)
    dev._ensure_connected = AsyncMock(side_effect=dev.cmd_enable_engineering_mode)
    await dev.initial_setup()
    assert dev.keys == [
        CMD_ENABLE_CFG + "0001",
        CMD_ENABLE_ENGINEERING,
        CMD_END_CFG,
        CMD_ENABLE_CFG + "0001",
        CMD_READ_PARAMS,
        CMD_END_CFG,
        CMD_ENABLE_CFG + "0001",
        CMD_GET_RES,
        CMD_END_CFG,
        CMD_ENABLE_CFG + "0001",
        CMD_GET_AUX,
        CMD_END_CFG,
    ]
    assert dev.parsed_data["move_gate_sensitivity"] == [1] * 9
    assert dev.parsed_data["still_gate_sensitivity"] == [2] * 9
    assert dev.parsed_data["absence_delay"] == 30
    assert dev.parsed_data["resolution"] == 0
    assert dev.parsed_data["light_threshold"] == 100
    assert dev.parsed_data["light_function"] == 1
    assert dev.parsed_data["light_out_level"] == 0


@pytest.mark.asyncio
async def test_set_absence_delay_success() -> None:
    """Set absence delay command sends correct key."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00",
            b"\x00\x00",
        ],
    )
    await dev.cmd_set_absence_delay(30)
    expected_payload = (
        CMD_SET_MAX_GATES_AND_NOBODY
        + PAR_MAX_MOVE_GATE
        + "08000000"
        + PAR_MAX_STILL_GATE
        + "08000000"
        + PAR_NOBODY_DURATION
        + "1e000000"
    )
    assert dev.keys == [CMD_ENABLE_CFG + "0001", expected_payload, CMD_END_CFG]
    assert dev.parsed_data["absence_delay"] == 30


@pytest.mark.asyncio
async def test_set_absence_delay_fail() -> None:
    """Set absence delay command raises on failure."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x01\x00",
            b"\x00\x00",
        ],
    )
    with pytest.raises(OperationError):
        await dev.cmd_set_absence_delay(30)
    expected_payload = (
        CMD_SET_MAX_GATES_AND_NOBODY
        + PAR_MAX_MOVE_GATE
        + "08000000"
        + PAR_MAX_STILL_GATE
        + "08000000"
        + PAR_NOBODY_DURATION
        + "1e000000"
    )
    assert dev.keys == [CMD_ENABLE_CFG + "0001", expected_payload]


@pytest.mark.asyncio
async def test_get_resolution_success() -> None:
    """Get resolution command parses response."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00\x01\x00",
            b"\x00\x00",
        ],
    )
    res = await dev.cmd_get_resolution()
    assert res == 1
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_GET_RES, CMD_END_CFG]


@pytest.mark.asyncio
async def test_get_resolution_fail() -> None:
    """Get resolution command raises on failure."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x01\x00\x01\x00",
        ],
    )
    with pytest.raises(OperationError):
        await dev.cmd_get_resolution()
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_GET_RES]


@pytest.mark.asyncio
async def test_set_resolution_success() -> None:
    """Set resolution command sends correct key."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00",
            b"\x00\x00",
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00",
            b"\x00\x00",
        ],
    )
    await dev.cmd_set_resolution(1)
    assert dev.keys == [
        CMD_ENABLE_CFG + "0001",
        CMD_SET_RES + "0100",
        CMD_END_CFG,
        CMD_ENABLE_CFG + "0001",
        CMD_REBOOT,
        CMD_END_CFG,
    ]
    assert dev.parsed_data["resolution"] == 1


@pytest.mark.asyncio
async def test_set_resolution_fail() -> None:
    """Set resolution command raises on failure."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x01\x00",
        ],
    )
    with pytest.raises(OperationError):
        await dev.cmd_set_resolution(1)
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_SET_RES + "0100"]


@pytest.mark.asyncio
async def test_reboot_success() -> None:
    """Reboot command sends correct key."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x00\x00",
            b"\x00\x00",
        ],
    )
    await dev.cmd_reboot()
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_REBOOT, CMD_END_CFG]


@pytest.mark.asyncio
async def test_reboot_fail() -> None:
    """Reboot command raises on failure."""
    dev = _TestDevice(
        password=None,
        response=[
            b"\x00\x00\x01\x00\x00@",
            b"\x01\x00",
        ],
    )
    with pytest.raises(OperationError):
        await dev.cmd_reboot()
    assert dev.keys == [CMD_ENABLE_CFG + "0001", CMD_REBOOT]


def test_unwrap_response():
    """Ensure responses are unwrapped correctly."""
    raw = bytes.fromhex("fdfcfbfa0400ff00010004030201")
    assert _unwrap_frame(raw, TX_HEADER, TX_FOOTER) == bytes.fromhex("ff000100")


def test_parse_response():
    """Ensure responses are parsed and ACK verified."""
    raw = bytes.fromhex("fdfcfbfa0400a801000004030201")
    dev = _TestDevice(password=None)
    assert dev._parse_response(CMD_BT_GET_PERMISSION, raw) == bytes.fromhex("0000")


@pytest.mark.parametrize("payload_hex", ["07", "09"])
def test_parse_response_rejects_short_payload(payload_hex: str) -> None:
    """Ensure single-byte payloads are rejected."""
    raw = bytes.fromhex(f"fdfcfbfa0100{payload_hex}04030201")
    dev = _TestDevice(password=None)
    with pytest.raises(OperationError):
        dev._parse_response(CMD_BT_GET_PERMISSION, raw)
