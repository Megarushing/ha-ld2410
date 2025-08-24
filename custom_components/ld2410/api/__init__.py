"""Library to handle device connection."""

from __future__ import annotations

from bleak_retry_connector import (
    close_stale_connections,
    close_stale_connections_by_address,
    get_device,
)

from .adv_parser import SupportedType, parse_advertisement_data
from .const import (
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_TIMEOUT,
    DEFAULT_SCAN_TIMEOUT,
    Model,
)
from .devices.device import Device, OperationError
from .devices.ld2410 import LD2410
from .discovery import GetDevices
from .models import Advertisement

__all__ = [
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_TIMEOUT",
    "DEFAULT_SCAN_TIMEOUT",
    "LD2410",
    "GetDevices",
    "Advertisement",
    "Device",
    "Model",
    "OperationError",
    "SupportedType",
    "close_stale_connections",
    "close_stale_connections_by_address",
    "get_device",
    "parse_advertisement_data",
]
