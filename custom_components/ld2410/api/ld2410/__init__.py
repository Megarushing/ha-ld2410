"""Library to handle connection with LD2410."""

from __future__ import annotations

from bleak_retry_connector import (
    close_stale_connections,
    close_stale_connections_by_address,
    get_device,
)

from .adv_parser import LD2410SupportedType, parse_advertisement_data
from .const import (
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_TIMEOUT,
    DEFAULT_SCAN_TIMEOUT,
    LD2410AccountConnectionError,
    LD2410ApiError,
    LD2410AuthenticationError,
    LD2410Model,
)
from .devices.device import LD2410Device, LD2410OperationError
from .devices.ld2410 import (
    LD2410,
)
from .discovery import GetLD2410Devices
from .models import LD2410Advertisement

__all__ = [
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_TIMEOUT",
    "DEFAULT_SCAN_TIMEOUT",
    "LD2410",
    "GetLD2410Devices",
    "LD2410AccountConnectionError",
    "LD2410Advertisement",
    "LD2410ApiError",
    "LD2410AuthenticationError",
    "LD2410Device",
    "LD2410Model",
    "LD2410OperationError",
    "LD2410SupportedType",
    "close_stale_connections",
    "close_stale_connections_by_address",
    "get_device",
    "parse_advertisement_data",
]
