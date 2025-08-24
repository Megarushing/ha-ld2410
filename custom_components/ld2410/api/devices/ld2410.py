"""Control commands for the device."""

from __future__ import annotations

import logging
from typing import Any, Sequence

from ..const import CMD_BT_PASSWORD
from .device import (
    Device,
    OperationError,
    update_after_operation,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_COMMAND_HEADER = "5701"

# Device command keys
PRESS_KEY = f"{DEVICE_COMMAND_HEADER}00"
ON_KEY = f"{DEVICE_COMMAND_HEADER}01"
OFF_KEY = f"{DEVICE_COMMAND_HEADER}02"
DOWN_KEY = f"{DEVICE_COMMAND_HEADER}03"
UP_KEY = f"{DEVICE_COMMAND_HEADER}04"


class LD2410(Device):
    """Representation of a device."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the device control class."""
        super().__init__(*args, **kwargs)
        self._inverse: bool = kwargs.pop("inverse_mode", False)

    async def cmd_send_bluetooth_password(
        self, words: Sequence[str] | None = None
    ) -> bytes | None:
        """Send the bluetooth password to the device."""
        payload_words = words or self._password_words
        if not payload_words:
            raise OperationError("Password required")
        payload = "".join(payload_words)
        key = CMD_BT_PASSWORD + payload
        response = await self._send_command(key)
        if response == b"\x01\x00":
            raise OperationError("Wrong password")
        return response

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None
        return {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "strength": _data[3],
            "timers": _data[8],
            "switchMode": bool(_data[9] & 16),
            "inverseDirection": bool(_data[9] & 1),
            "holdSeconds": _data[10],
        }
