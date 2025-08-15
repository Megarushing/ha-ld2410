"""Library to handle connection with LD2410."""

from __future__ import annotations

from bleak_retry_connector import (
    close_stale_connections,
    close_stale_connections_by_address,
    get_device,
)

from .adv_parser import LD2410SupportedType, parse_advertisement_data
from .const import (
    AirPurifierMode,
    BulbColorMode,
    CeilingLightColorMode,
    ColorMode,
    FanMode,
    HumidifierAction,
    HumidifierMode,
    HumidifierWaterLevel,
    LD2410AccountConnectionError,
    LD2410ApiError,
    LD2410AuthenticationError,
    LD2410Model,
    LockStatus,
    StripLightColorMode,
)
from .devices.air_purifier import LD2410AirPurifier
from .devices.base_light import LD2410BaseLight
from .devices.blind_tilt import LD2410BlindTilt
from .devices.bot import LD2410
from .devices.bulb import LD2410Bulb
from .devices.ceiling_light import LD2410CeilingLight
from .devices.curtain import LD2410Curtain
from .devices.device import (
    LD2410Device,
    LD2410EncryptedDevice,
    LD2410OperationError,
)
from .devices.evaporative_humidifier import LD2410EvaporativeHumidifier
from .devices.fan import LD2410Fan
from .devices.humidifier import LD2410Humidifier
from .devices.light_strip import LD2410LightStrip, LD2410StripLight3
from .devices.lock import LD2410Lock
from .devices.plug import LD2410PlugMini
from .devices.relay_switch import (
    LD2410GarageDoorOpener,
    LD2410RelaySwitch,
    LD2410RelaySwitch2PM,
)
from .devices.roller_shade import LD2410RollerShade
from .devices.vacuum import LD2410Vacuum
from .discovery import GetLD2410Devices
from .models import LD2410Advertisement

__all__ = [
    "LD2410",
    "LD2410",
    "AirPurifierMode",
    "BulbColorMode",
    "CeilingLightColorMode",
    "ColorMode",
    "FanMode",
    "GetLD2410Devices",
    "HumidifierAction",
    "HumidifierMode",
    "HumidifierWaterLevel",
    "LD2410AccountConnectionError",
    "LD2410Advertisement",
    "LD2410AirPurifier",
    "LD2410ApiError",
    "LD2410AuthenticationError",
    "LD2410BaseLight",
    "LD2410BlindTilt",
    "LD2410Bulb",
    "LD2410CeilingLight",
    "LD2410Curtain",
    "LD2410Device",
    "LD2410EncryptedDevice",
    "LD2410EvaporativeHumidifier",
    "LD2410Fan",
    "LD2410GarageDoorOpener",
    "LD2410Humidifier",
    "LD2410LightStrip",
    "LD2410Lock",
    "LD2410Model",
    "LD2410Model",
    "LD2410OperationError",
    "LD2410PlugMini",
    "LD2410PlugMini",
    "LD2410RelaySwitch",
    "LD2410RelaySwitch2PM",
    "LD2410RollerShade",
    "LD2410StripLight3",
    "LD2410SupportedType",
    "LD2410SupportedType",
    "LD2410Vacuum",
    "LockStatus",
    "StripLightColorMode",
    "close_stale_connections",
    "close_stale_connections_by_address",
    "get_device",
    "parse_advertisement_data",
]
