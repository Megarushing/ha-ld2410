"""Library to handle connection with LD2410."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bleak.backends.device import BLEDevice


@dataclass
class Advertisement:
    """Advertisement from an LD2410 device."""

    address: str
    data: dict[str, Any]
    device: BLEDevice
    rssi: int
    active: bool = False
