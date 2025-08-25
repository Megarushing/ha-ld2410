"""Control commands for the device."""

from __future__ import annotations

import logging
from typing import Any, Dict, Sequence

from bleak_retry_connector import BleakClientWithServiceCache

from ..const import (
    CMD_BT_GET_PERMISSION,
    CMD_ENABLE_CFG,
    CMD_END_CFG,
    CMD_ENABLE_ENGINEERING,
)
from .device import Device, OperationError

_LOGGER = logging.getLogger(__name__)


class LD2410(Device):
    """Representation of a device."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the device control class."""
        super().__init__(*args, **kwargs)
        self._inverse: bool = kwargs.pop("inverse_mode", False)

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Handle disconnection and schedule reconnect."""
        super()._disconnected(client)
        if not self._expected_disconnect:
            self.loop.create_task(self._restart_connection())

    async def _restart_connection(self) -> None:
        """Reconnect and reauthorize after an unexpected disconnect."""
        try:
            _LOGGER.debug("%s: Reconnecting...", self.name)
            await self._ensure_connected()
            if self._password_words:
                await self.cmd_send_bluetooth_password()
        except Exception as ex:  # pragma: no cover - best effort
            _LOGGER.debug("%s: Reconnect failed: %s", self.name, ex)

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection and schedule reconnect."""
        await super()._execute_timed_disconnect()
        self.loop.create_task(self._restart_connection())

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
        key = CMD_BT_GET_PERMISSION + payload
        response = await self._send_command(key)
        if response == b"\x01\x00":
            raise OperationError("Wrong password")
        return response == b"\x00\x00"

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
        response = await self._send_command(CMD_ENABLE_ENGINEERING)
        if response != b"\x00\x00":
            raise OperationError("Failed to enable engineering mode")

    def parse_intra_frame(self, data: bytes) -> Dict[str, Any] | None:
        """Parse an uplink intra frame.

        ``data`` must be the payload after removing the frame header and footer.
        Returns ``None`` if the payload is not an intra frame and raises
        ``ValueError`` if the frame is malformed.
        """
        if len(data) < 2 or data[1] != 0xAA:
            # Not an intra frame
            return None

        frame_type = data[0]
        if frame_type == 0x01:
            ftype = "engineering"
        elif frame_type == 0x02:
            ftype = "basic"
        else:
            raise ValueError(f"unknown frame type {frame_type:#x}")

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
            result.update(
                {
                    "max_move_gate": max_move_gate,
                    "max_still_gate": max_still_gate,
                    "move_gate_energy": move_gate_energy,
                    "still_gate_energy": still_gate_energy,
                }
            )

        return result
