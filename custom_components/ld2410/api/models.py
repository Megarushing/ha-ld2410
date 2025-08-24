"""Library to handle device connection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bleak.backends.device import BLEDevice


@dataclass
class Advertisement:
    """Advertisement from a device."""

    address: str
    data: dict[str, Any]
    device: BLEDevice
    rssi: int
    active: bool = False
