"""Library to handle connection with LD2410."""

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
    AccountConnectionError,
    ApiError,
    AuthenticationError,
    Model,
)
from .devices.device import Device, OperationError
from .devices.device_control import LD2410
from .discovery import GetDevices
from .models import Advertisement

__all__ = [
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_TIMEOUT",
    "DEFAULT_SCAN_TIMEOUT",
    "LD2410",
    "GetDevices",
    "AccountConnectionError",
    "Advertisement",
    "ApiError",
    "AuthenticationError",
    "Device",
    "Model",
    "OperationError",
    "SupportedType",
    "close_stale_connections",
    "close_stale_connections_by_address",
    "get_device",
    "parse_advertisement_data",
]
