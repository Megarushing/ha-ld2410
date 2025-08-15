"""LD2410 Device Consts Library."""

from __future__ import annotations

from ..enum import StrEnum

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5


class LD2410ApiError(RuntimeError):
    """Raised when an API call fails."""


class LD2410AuthenticationError(RuntimeError):
    """Raised when authentication fails."""


class LD2410AccountConnectionError(RuntimeError):
    """Raised when connection to the LD2410 account fails."""


class LD2410Model(StrEnum):
    """LD2410 device models."""

    CONTACT_SENSOR = "WoContact"
    MOTION_SENSOR = "WoPresence"
    LD2410 = "HLK-LD2410B"


__all__ = [
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_TIMEOUT",
    "DEFAULT_SCAN_TIMEOUT",
    "LD2410AccountConnectionError",
    "LD2410ApiError",
    "LD2410AuthenticationError",
    "LD2410Model",
]
