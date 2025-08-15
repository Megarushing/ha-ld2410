"""LD2410 Device Consts Library."""

from __future__ import annotations

from ..enum import StrEnum
from .air_purifier import AirPurifierMode
from .evaporative_humidifier import (
    HumidifierAction,
    HumidifierMode,
    HumidifierWaterLevel,
)
from .fan import FanMode
from .light import (
    BulbColorMode,
    CeilingLightColorMode,
    ColorMode,
    StripLightColorMode,
)

# Preserve old LockStatus export for backwards compatibility
from .lock import LockStatus

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5


class LD2410ApiError(RuntimeError):
    """
    Raised when API call fails.

    This exception inherits from RuntimeError to avoid breaking existing code
    but will be changed to Exception in a future release.
    """


class LD2410AuthenticationError(RuntimeError):
    """
    Raised when authentication fails.

    This exception inherits from RuntimeError to avoid breaking existing code
    but will be changed to Exception in a future release.
    """


class LD2410AccountConnectionError(RuntimeError):
    """
    Raised when connection to LD2410 account fails.

    This exception inherits from RuntimeError to avoid breaking existing code
    but will be changed to Exception in a future release.
    """


class LD2410Model(StrEnum):
    BOT = "WoHand"
    CURTAIN = "WoCurtain"
    HUMIDIFIER = "WoHumi"
    PLUG_MINI = "WoPlug"
    CONTACT_SENSOR = "WoContact"
    LIGHT_STRIP = "WoStrip"
    METER = "WoSensorTH"
    METER_PRO = "WoTHP"
    METER_PRO_C = "WoTHPc"
    IO_METER = "WoIOSensorTH"
    MOTION_SENSOR = "WoPresence"
    COLOR_BULB = "WoBulb"
    CEILING_LIGHT = "WoCeiling"
    LOCK = "WoLock"
    LOCK_PRO = "WoLockPro"
    BLIND_TILT = "WoBlindTilt"
    HUB2 = "WoHub2"
    LEAK = "Leak Detector"
    KEYPAD = "WoKeypad"
    RELAY_SWITCH_1PM = "Relay Switch 1PM"
    RELAY_SWITCH_1 = "Relay Switch 1"
    REMOTE = "WoRemote"
    EVAPORATIVE_HUMIDIFIER = "Evaporative Humidifier"
    ROLLER_SHADE = "Roller Shade"
    HUBMINI_MATTER = "HubMini Matter"
    CIRCULATOR_FAN = "Circulator Fan"
    K20_VACUUM = "K20 Vacuum"
    S10_VACUUM = "S10 Vacuum"
    K10_VACUUM = "K10+ Vacuum"
    K10_PRO_VACUUM = "K10+ Pro Vacuum"
    K10_PRO_COMBO_VACUUM = "K10+ Pro Combo Vacuum"
    AIR_PURIFIER = "Air Purifier"
    AIR_PURIFIER_TABLE = "Air Purifier Table"
    HUB3 = "Hub3"
    LOCK_ULTRA = "Lock Ultra"
    LOCK_LITE = "Lock Lite"
    GARAGE_DOOR_OPENER = "Garage Door Opener"
    RELAY_SWITCH_2PM = "Relay Switch 2PM"
    STRIP_LIGHT_3 = "Strip Light 3"
    FLOOR_LAMP = "Floor Lamp"
    LD2410 = "HLK-LD2410B"


__all__ = [
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_TIMEOUT",
    "DEFAULT_SCAN_TIMEOUT",
    "AirPurifierMode",
    "BulbColorMode",
    "CeilingLightColorMode",
    "ColorMode",
    "FanMode",
    "HumidifierAction",
    "HumidifierMode",
    "HumidifierWaterLevel",
    "LD2410AccountConnectionError",
    "LD2410ApiError",
    "LD2410AuthenticationError",
    "LD2410Model",
    "LockStatus",
    "StripLightColorMode",
]
