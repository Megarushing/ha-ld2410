"""Constants for the ld2410 integration."""

from enum import StrEnum

from .api import ld2410
from .api.ld2410 import LD2410Model

DOMAIN = "ld2410"
MANUFACTURER = "ld2410"

# Config Attributes

DEFAULT_NAME = "LD2410"


class SupportedModels(StrEnum):
    """Supported LD2410 models."""

    BOT = "bot"
    BULB = "bulb"
    CEILING_LIGHT = "ceiling_light"
    CURTAIN = "curtain"
    HYGROMETER = "hygrometer"
    HYGROMETER_CO2 = "hygrometer_co2"
    LIGHT_STRIP = "light_strip"
    CONTACT = "contact"
    PLUG = "plug"
    MOTION = "motion"
    HUMIDIFIER = "humidifier"
    LOCK = "lock"
    LOCK_PRO = "lock_pro"
    BLIND_TILT = "blind_tilt"
    HUB2 = "hub2"
    RELAY_SWITCH_1PM = "relay_switch_1pm"
    RELAY_SWITCH_1 = "relay_switch_1"
    LEAK = "leak"
    REMOTE = "remote"
    ROLLER_SHADE = "roller_shade"
    HUBMINI_MATTER = "hubmini_matter"
    CIRCULATOR_FAN = "circulator_fan"
    K20_VACUUM = "k20_vacuum"
    S10_VACUUM = "s10_vacuum"
    K10_VACUUM = "k10_vacuum"
    K10_PRO_VACUUM = "k10_pro_vacuum"
    K10_PRO_COMBO_VACUUM = "k10_pro_combo_vacumm"
    HUB3 = "hub3"
    LOCK_LITE = "lock_lite"
    LOCK_ULTRA = "lock_ultra"
    AIR_PURIFIER = "air_purifier"
    AIR_PURIFIER_TABLE = "air_purifier_table"
    EVAPORATIVE_HUMIDIFIER = "evaporative_humidifier"
    FLOOR_LAMP = "floor_lamp"
    STRIP_LIGHT_3 = "strip_light_3"
    LD2410 = "ld2410"


CONNECTABLE_SUPPORTED_MODEL_TYPES = {
    LD2410Model.BOT: SupportedModels.BOT,
    LD2410Model.CURTAIN: SupportedModels.CURTAIN,
    LD2410Model.PLUG_MINI: SupportedModels.PLUG,
    LD2410Model.COLOR_BULB: SupportedModels.BULB,
    LD2410Model.LIGHT_STRIP: SupportedModels.LIGHT_STRIP,
    LD2410Model.CEILING_LIGHT: SupportedModels.CEILING_LIGHT,
    LD2410Model.HUMIDIFIER: SupportedModels.HUMIDIFIER,
    LD2410Model.LOCK: SupportedModels.LOCK,
    LD2410Model.LOCK_PRO: SupportedModels.LOCK_PRO,
    LD2410Model.BLIND_TILT: SupportedModels.BLIND_TILT,
    LD2410Model.HUB2: SupportedModels.HUB2,
    LD2410Model.RELAY_SWITCH_1PM: SupportedModels.RELAY_SWITCH_1PM,
    LD2410Model.RELAY_SWITCH_1: SupportedModels.RELAY_SWITCH_1,
    LD2410Model.ROLLER_SHADE: SupportedModels.ROLLER_SHADE,
    LD2410Model.CIRCULATOR_FAN: SupportedModels.CIRCULATOR_FAN,
    LD2410Model.K20_VACUUM: SupportedModels.K20_VACUUM,
    LD2410Model.S10_VACUUM: SupportedModels.S10_VACUUM,
    LD2410Model.K10_VACUUM: SupportedModels.K10_VACUUM,
    LD2410Model.K10_PRO_VACUUM: SupportedModels.K10_PRO_VACUUM,
    LD2410Model.K10_PRO_COMBO_VACUUM: SupportedModels.K10_PRO_COMBO_VACUUM,
    LD2410Model.LOCK_LITE: SupportedModels.LOCK_LITE,
    LD2410Model.LOCK_ULTRA: SupportedModels.LOCK_ULTRA,
    LD2410Model.AIR_PURIFIER: SupportedModels.AIR_PURIFIER,
    LD2410Model.AIR_PURIFIER_TABLE: SupportedModels.AIR_PURIFIER_TABLE,
    LD2410Model.EVAPORATIVE_HUMIDIFIER: SupportedModels.EVAPORATIVE_HUMIDIFIER,
    LD2410Model.FLOOR_LAMP: SupportedModels.FLOOR_LAMP,
    LD2410Model.STRIP_LIGHT_3: SupportedModels.STRIP_LIGHT_3,
}

NON_CONNECTABLE_SUPPORTED_MODEL_TYPES = {
    LD2410Model.METER: SupportedModels.HYGROMETER,
    LD2410Model.IO_METER: SupportedModels.HYGROMETER,
    LD2410Model.METER_PRO: SupportedModels.HYGROMETER,
    LD2410Model.METER_PRO_C: SupportedModels.HYGROMETER_CO2,
    LD2410Model.CONTACT_SENSOR: SupportedModels.CONTACT,
    LD2410Model.MOTION_SENSOR: SupportedModels.MOTION,
    LD2410Model.LEAK: SupportedModels.LEAK,
    LD2410Model.REMOTE: SupportedModels.REMOTE,
    LD2410Model.HUBMINI_MATTER: SupportedModels.HUBMINI_MATTER,
    LD2410Model.HUB3: SupportedModels.HUB3,
    LD2410Model.LD2410: SupportedModels.LD2410,
}

SUPPORTED_MODEL_TYPES = (
    CONNECTABLE_SUPPORTED_MODEL_TYPES | NON_CONNECTABLE_SUPPORTED_MODEL_TYPES
)

ENCRYPTED_MODELS = {
    LD2410Model.RELAY_SWITCH_1,
    LD2410Model.RELAY_SWITCH_1PM,
    LD2410Model.LOCK,
    LD2410Model.LOCK_PRO,
    LD2410Model.LOCK_LITE,
    LD2410Model.LOCK_ULTRA,
    LD2410Model.AIR_PURIFIER,
    LD2410Model.AIR_PURIFIER_TABLE,
    LD2410Model.EVAPORATIVE_HUMIDIFIER,
    LD2410Model.FLOOR_LAMP,
    LD2410Model.STRIP_LIGHT_3,
}

ENCRYPTED_LD2410_MODEL_TO_CLASS: dict[LD2410Model, ld2410.LD2410EncryptedDevice] = {
    LD2410Model.LOCK: ld2410.LD2410Lock,
    LD2410Model.LOCK_PRO: ld2410.LD2410Lock,
    LD2410Model.RELAY_SWITCH_1PM: ld2410.LD2410RelaySwitch,
    LD2410Model.RELAY_SWITCH_1: ld2410.LD2410RelaySwitch,
    LD2410Model.LOCK_LITE: ld2410.LD2410Lock,
    LD2410Model.LOCK_ULTRA: ld2410.LD2410Lock,
    LD2410Model.AIR_PURIFIER: ld2410.LD2410AirPurifier,
    LD2410Model.AIR_PURIFIER_TABLE: ld2410.LD2410AirPurifier,
    LD2410Model.EVAPORATIVE_HUMIDIFIER: ld2410.LD2410EvaporativeHumidifier,
    LD2410Model.FLOOR_LAMP: ld2410.LD2410StripLight3,
    LD2410Model.STRIP_LIGHT_3: ld2410.LD2410StripLight3,
}

HASS_SENSOR_TYPE_TO_LD2410_MODEL = {str(v): k for k, v in SUPPORTED_MODEL_TYPES.items()}

# Config Defaults
DEFAULT_RETRY_COUNT = 3
DEFAULT_LOCK_NIGHTLATCH = False

# Config Options
CONF_RETRY_COUNT = "retry_count"
CONF_KEY_ID = "key_id"
CONF_ENCRYPTION_KEY = "encryption_key"
CONF_LOCK_NIGHTLATCH = "lock_force_nightlatch"
