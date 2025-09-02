"""Control commands for the device."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Sequence

from bleak.backends.device import BLEDevice

from ..const import (
    CMD_BT_GET_PERMISSION,
    CMD_BT_SET_PWD,
    CMD_ENABLE_CFG,
    CMD_END_CFG,
    CMD_ENABLE_ENGINEERING,
    CMD_REBOOT,
    CMD_READ_PARAMS,
    CMD_START_AUTO_THRESH,
    CMD_QUERY_AUTO_THRESH,
    CMD_SET_MAX_GATES_AND_NOBODY,
    CMD_SET_SENSITIVITY,
    CMD_SET_RES,
    CMD_GET_RES,
    CMD_SET_AUX,
    CMD_GET_AUX,
    PAR_DISTANCE_GATE,
    PAR_MOVE_SENS,
    PAR_STILL_SENS,
    PAR_MAX_MOVE_GATE,
    PAR_MAX_STILL_GATE,
    PAR_NOBODY_DURATION,
    UPLINK_TYPE_BASIC,
    UPLINK_TYPE_ENGINEERING,
    TX_HEADER,
    TX_FOOTER,
    RX_HEADER,
    RX_FOOTER,
)
from .device import Device, OperationError

_LOGGER = logging.getLogger(__name__)


def _password_to_words(password: str) -> tuple[str, ...]:
    """Encode an ASCII password into 16-bit word hex strings."""
    data = password.encode("ascii")
    if len(data) % 2:
        data += b"\x00"
    return tuple(data[i : i + 2].hex() for i in range(0, len(data), 2))


def _unwrap_frame(data: bytes, header: str, footer: str) -> bytes:
    """Remove header and footer from a framed message."""
    hdr = bytearray.fromhex(header)
    ftr = bytearray.fromhex(footer)
    if data.startswith(hdr) and data.endswith(ftr):
        length = int.from_bytes(data[len(hdr) : len(hdr) + 2], "little")
        return data[len(hdr) + 2 : len(hdr) + 2 + length]
    return data


class LD2410(Device):
    """Representation of a device."""

    _auto_reconnect: bool = True
    _default_should_wait_for_response: bool = True

    def __init__(
        self,
        device: BLEDevice,
        password: str | None = None,
        interface: int = 0,
        **kwargs: Any,
    ) -> None:
        """Initialize the device control class."""
        self._inverse: bool = kwargs.pop("inverse_mode", False)
        super().__init__(device, interface=interface, **kwargs)
        self._password_words = _password_to_words(password) if password else ()

    async def _on_connect(self) -> None:
        """Reauthorize and refresh configuration after connecting."""
        if self._password_words:
            await self.cmd_send_bluetooth_password()
        await self.cmd_enable_engineering_mode()
        params = await self.cmd_read_params()
        res = await self.cmd_get_resolution()
        await self.cmd_get_light_config()
        self._update_parsed_data(
            {
                "move_gate_sensitivity": params.get("move_gate_sensitivity"),
                "still_gate_sensitivity": params.get("still_gate_sensitivity"),
                "absence_delay": params.get("absence_delay"),
                "max_move_gate": params.get("max_move_gate"),
                "max_still_gate": params.get("max_still_gate"),
                "resolution": res,
            }
        )
        _LOGGER.info(
            "%s: Negotiation complete, start receiving uplink frames…",
            self.name,
        )

    def _modify_command(self, raw_command: str) -> bytes:
        command_word = raw_command[:4]
        value = raw_command[4:]
        contents = bytearray.fromhex(command_word + value)
        length = len(contents).to_bytes(2, "little")
        return (
            bytearray.fromhex(TX_HEADER)
            + length
            + contents
            + bytearray.fromhex(TX_FOOTER)
        )

    def _parse_response(self, raw_command: str, data: bytes) -> bytes:
        payload = _unwrap_frame(data, TX_HEADER, TX_FOOTER)
        if len(payload) < 2:
            raise OperationError("Response too short")
        expected_ack = (int(raw_command[:4], 16) ^ 0x0001).to_bytes(2, "big")
        command = payload[:2]
        if command != expected_ack:
            raise OperationError(
                f"Unexpected response command {command.hex()} for {raw_command[:4]}"
            )
        return payload[2:]

    def _handle_notification(self, data: bytearray) -> bool:
        if data.startswith(bytearray.fromhex(TX_HEADER)):
            if self._notify_future and not self._notify_future.done():
                self._notify_future.set_result(data)
            else:
                _LOGGER.debug(
                    "%s: Received unexpected command response: %s",
                    self.name,
                    data.hex(),
                )
            return True
        if data.startswith(bytearray.fromhex(RX_HEADER)):
            payload = _unwrap_frame(data, RX_HEADER, RX_FOOTER)
            try:
                parsed = self._parse_uplink_frame(payload)
            except Exception as err:  # pragma: no cover - defensive
                _LOGGER.error("%s: Failed to parse uplink frame: %s", self.name, err)
            else:
                if parsed and self._update_parsed_data(parsed):
                    self._last_full_update = time.monotonic()
                    self._fire_callbacks()
            return True
        return False

    async def cmd_send_bluetooth_password(
        self, words: Sequence[str] | None = None
    ) -> bool:
        """Send the bluetooth password to the device.

        Returns True if the password is accepted.
        """
        payload_words = words or self._password_words
        if not payload_words:
            raise OperationError("Password required")
        payload = "".join(payload_words)
        raw_command = CMD_BT_GET_PERMISSION + payload
        response = await self._send_command(raw_command)
        if response == b"\x01\x00":
            raise OperationError("Wrong password")
        return response == b"\x00\x00"

    async def cmd_set_bluetooth_password(self, password: str) -> None:
        """Set a new bluetooth password on the device."""
        if len(password) != 6:
            raise ValueError("password must be 6 characters")
        try:
            words = _password_to_words(password)
        except UnicodeEncodeError as err:
            raise ValueError("password must be ASCII") from err
        await self.cmd_enable_config()
        payload = "".join(words)
        response = await self._send_command(CMD_BT_SET_PWD + payload)
        if response != b"\x00\x00":
            raise OperationError("Failed to set bluetooth password")
        await self.cmd_end_config()
        self._password_words = words

    async def cmd_enable_config(self) -> tuple[int, int]:
        """Enable configuration session.

        Returns the protocol version and buffer size.
        """
        response = await self._send_command(CMD_ENABLE_CFG + "0001")
        if not response or len(response) < 6 or response[:2] != b"\x00\x00":
            raise OperationError("Failed to enable configuration")
        proto_ver = int.from_bytes(response[2:4], "little")
        buf_size = int.from_bytes(response[4:6], "little")
        return proto_ver, buf_size

    async def cmd_end_config(self) -> None:
        """End configuration session."""
        response = await self._send_command(CMD_END_CFG)
        if response != b"\x00\x00":
            raise OperationError("Failed to end configuration")

    async def cmd_enable_engineering_mode(self) -> None:
        """Enable engineering mode."""
        await self.cmd_enable_config()
        response = await self._send_command(CMD_ENABLE_ENGINEERING)
        if response != b"\x00\x00":
            raise OperationError("Failed to enable engineering mode")
        await self.cmd_end_config()

    async def cmd_auto_thresholds(self, duration_sec: int) -> None:
        """Start automatic threshold detection for the specified duration."""
        if not 0 <= duration_sec <= 0xFFFF:
            raise ValueError("duration_sec must be 0..65535")
        await self.cmd_enable_config()
        raw_command = CMD_START_AUTO_THRESH + duration_sec.to_bytes(2, "little").hex()
        response = await self._send_command(raw_command)
        if response != b"\x00\x00":
            raise OperationError("Failed to start automatic threshold detection")
        await self.cmd_end_config()

    async def cmd_query_auto_thresholds(self) -> int:
        """Query automatic threshold detection status."""
        await self.cmd_enable_config()
        response = await self._send_command(CMD_QUERY_AUTO_THRESH)
        if not response or len(response) < 4 or response[:2] != b"\x00\x00":
            raise OperationError("Failed to query automatic threshold status")
        r = int.from_bytes(response[2:4], "little")
        await self.cmd_end_config()
        return r

    async def cmd_set_gate_sensitivity(self, gate: int, move: int, still: int) -> None:
        """Set move and still sensitivity for a gate."""
        if not 0 <= gate <= 8:
            raise ValueError("gate must be 0..8")
        if not 0 <= move <= 100:
            raise ValueError("move must be 0..100")
        if not 0 <= still <= 100:
            raise ValueError("still must be 0..100")
        await self.cmd_enable_config()
        payload = (
            PAR_DISTANCE_GATE
            + gate.to_bytes(4, "little").hex()
            + PAR_MOVE_SENS
            + move.to_bytes(4, "little").hex()
            + PAR_STILL_SENS
            + still.to_bytes(4, "little").hex()
        )
        response = await self._send_command(CMD_SET_SENSITIVITY + payload)
        if response != b"\x00\x00":
            raise OperationError("Failed to set sensitivity")
        move_list = list(self.parsed_data.get("move_gate_sensitivity") or [])
        still_list = list(self.parsed_data.get("still_gate_sensitivity") or [])
        if gate < len(move_list):
            move_list[gate] = move
        if gate < len(still_list):
            still_list[gate] = still
        self._update_parsed_data(
            {
                "move_gate_sensitivity": move_list,
                "still_gate_sensitivity": still_list,
            }
        )
        await self.cmd_end_config()

    async def cmd_read_params(self) -> Dict[str, Any]:
        """Read and parse device configuration parameters."""
        await self.cmd_enable_config()
        response = await self._send_command(CMD_READ_PARAMS)
        if (
            not response
            or len(response) < 10
            or response[:2] != b"\x00\x00"
            or response[2] != 0xAA
        ):
            raise OperationError("Failed to read parameters")
        payload = response[3:]
        max_gate = payload[0]
        max_move_gate = payload[1]
        max_still_gate = payload[2]
        move_len = max_gate + 1
        expected_len = 3 + move_len * 2 + 2
        if len(payload) < expected_len:
            raise OperationError("Failed to read parameters")
        idx = 3
        move_gate_sensitivity = list(payload[idx : idx + move_len])
        idx += move_len
        still_gate_sensitivity = list(payload[idx : idx + move_len])
        idx += move_len
        absence_delay = int.from_bytes(payload[idx : idx + 2], "little")
        r = {
            "max_gate": max_gate,
            "max_move_gate": max_move_gate,
            "max_still_gate": max_still_gate,
            "move_gate_sensitivity": move_gate_sensitivity,
            "still_gate_sensitivity": still_gate_sensitivity,
            "absence_delay": absence_delay,
        }
        await self.cmd_end_config()
        return r

    async def cmd_set_absence_delay(self, delay: int) -> None:
        """Set the absence delay (no-one duration)."""
        if not 0 <= delay <= 65535:
            raise ValueError("delay must be 0..65535")
        move_gate = self.parsed_data.get("max_move_gate", 8)
        still_gate = self.parsed_data.get("max_still_gate", 8)
        await self.cmd_enable_config()
        payload = (
            PAR_MAX_MOVE_GATE
            + move_gate.to_bytes(4, "little").hex()
            + PAR_MAX_STILL_GATE
            + still_gate.to_bytes(4, "little").hex()
            + PAR_NOBODY_DURATION
            + delay.to_bytes(4, "little").hex()
        )
        response = await self._send_command(CMD_SET_MAX_GATES_AND_NOBODY + payload)
        if response != b"\x00\x00":
            raise OperationError("Failed to set absence delay")
        self._update_parsed_data({"absence_delay": delay})
        await self.cmd_end_config()

    async def cmd_get_light_config(self) -> Dict[str, int]:
        """Get light control configuration."""
        await self.cmd_enable_config()
        response = await self._send_command(CMD_GET_AUX)
        if not response or len(response) < 6 or response[:2] != b"\x00\x00":
            raise OperationError("Failed to get light config")
        mode = response[2]
        threshold = response[3]
        out_level = response[4]
        self._update_parsed_data(
            {
                "light_function": mode,
                "light_threshold": threshold,
                "light_out_level": out_level,
            }
        )
        await self.cmd_end_config()
        return {"mode": mode, "threshold": threshold, "out_level": out_level}

    async def cmd_set_light_config(
        self,
        *,
        mode: int | None = None,
        threshold: int | None = None,
        out_level: int | None = None,
    ) -> None:
        """Set light control configuration."""
        if mode is not None and mode not in (0, 1, 2):
            raise ValueError("mode must be 0, 1, or 2")
        if threshold is not None and not 0 <= threshold <= 255:
            raise ValueError("threshold must be 0..255")
        if out_level is not None and out_level not in (0, 1):
            raise ValueError("out_level must be 0 or 1")
        current_mode = self.parsed_data.get("light_function", 0)
        current_threshold = self.parsed_data.get("light_threshold", 0x80)
        current_out_level = self.parsed_data.get("light_out_level", 0)
        mode_byte = mode if mode is not None else current_mode
        threshold_byte = threshold if threshold is not None else current_threshold
        out_level_byte = out_level if out_level is not None else current_out_level
        payload = bytes([mode_byte, threshold_byte, out_level_byte, 0]).hex()
        await self.cmd_enable_config()
        response = await self._send_command(CMD_SET_AUX + payload)
        if response != b"\x00\x00":
            raise OperationError("Failed to set light config")
        self._update_parsed_data(
            {
                "light_function": mode_byte,
                "light_threshold": threshold_byte,
                "light_out_level": out_level_byte,
            }
        )
        await self.cmd_end_config()

    async def cmd_get_resolution(self) -> int:
        """Query the distance resolution."""
        await self.cmd_enable_config()
        response = await self._send_command(CMD_GET_RES)
        if not response or len(response) < 4 or response[:2] != b"\x00\x00":
            raise OperationError("Failed to get resolution")
        idx = int.from_bytes(response[2:4], "little")
        await self.cmd_end_config()
        self._update_parsed_data({"resolution": idx})
        return idx

    async def cmd_set_resolution(self, index: int) -> None:
        """Set the distance resolution."""
        if index not in (0, 1):
            raise ValueError("index must be 0 or 1")
        await self.cmd_enable_config()
        payload = index.to_bytes(2, "little").hex()
        response = await self._send_command(CMD_SET_RES + payload)
        if response != b"\x00\x00":
            raise OperationError("Failed to set resolution")
        self._update_parsed_data({"resolution": index})
        await self.cmd_end_config()
        await self.cmd_reboot()

    async def cmd_reboot(self) -> None:
        """Reboot the module."""
        await self.cmd_enable_config()
        await self._send_command(CMD_REBOOT, wait_for_response=False)

    def _parse_uplink_frame(self, data: bytes) -> Dict[str, Any] | None:
        """Parse an uplink frame.

        ``data`` must be the payload after removing the frame header and footer.
        Returns ``None`` if the payload is not an uplink frame and raises
        ``ValueError`` if the frame is malformed.
        """
        if len(data) < 2 or data[1] != 0xAA:
            # Not an uplink frame
            return None

        frame_type = data[:1].hex()
        if frame_type == UPLINK_TYPE_ENGINEERING:
            ftype = "engineering"
        elif frame_type == UPLINK_TYPE_BASIC:
            ftype = "basic"
        else:
            raise ValueError(f"unknown frame type {frame_type}")

        if not data.endswith(b"\x55\x00"):
            raise ValueError("missing frame footer")

        content = data[2:-2]
        if len(content) < 9:
            raise ValueError("payload too short for basic data")
        status_raw = content[0]
        move_distance_cm = int.from_bytes(content[1:3], "little")
        move_energy = content[3]
        still_distance_cm = int.from_bytes(content[4:6], "little")
        still_energy = content[6]
        detect_distance_cm = int.from_bytes(content[7:9], "little")
        idx = 9

        moving = status_raw in (0x01, 0x03)
        stationary = status_raw in (0x02, 0x03)
        occupancy = moving or stationary

        result: Dict[str, Any] = {
            "type": ftype,
            "moving": moving,
            "stationary": stationary,
            "occupancy": occupancy,
            "move_distance_cm": move_distance_cm,
            "move_energy": move_energy,
            "still_distance_cm": still_distance_cm,
            "still_energy": still_energy,
            "detect_distance_cm": detect_distance_cm,
        }

        if ftype == "engineering":
            if len(content) < idx + 2:
                raise ValueError("missing gate counts")
            max_move_gate = content[idx]
            max_still_gate = content[idx + 1]
            idx += 2
            move_len = max_move_gate + 1
            still_len = max_still_gate + 1
            if len(content) < idx + move_len + still_len:
                raise ValueError("missing gate energy values")
            move_gate_energy = list(content[idx : idx + move_len])
            idx += move_len
            still_gate_energy = list(content[idx : idx + still_len])
            idx += still_len
            if len(content) < idx + 2:
                raise ValueError("missing photo sensor or OUT pin status")
            photo_sensor = content[idx]
            out_pin = content[idx + 1]
            result.update(
                {
                    "max_move_gate": max_move_gate,
                    "max_still_gate": max_still_gate,
                    "move_gate_energy": move_gate_energy,
                    "still_gate_energy": still_gate_energy,
                    "photo_sensor": photo_sensor,
                    "out_pin": bool(out_pin),
                }
            )

        return result
