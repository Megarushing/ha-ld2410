"""Constants for the ld2410 integration."""

from enum import StrEnum

from .api.ld2410 import LD2410Model

DOMAIN = "ld2410"
MANUFACTURER = "ld2410"

# Config Attributes

DEFAULT_NAME = "LD2410"


class SupportedModels(StrEnum):
    """Supported LD2410 models."""

    CONTACT = "contact"
    MOTION = "motion"
    LD2410 = "ld2410"


CONNECTABLE_SUPPORTED_MODEL_TYPES: dict[LD2410Model, SupportedModels] = {
    LD2410Model.LD2410: SupportedModels.LD2410,
}

NON_CONNECTABLE_SUPPORTED_MODEL_TYPES = {
    LD2410Model.CONTACT_SENSOR: SupportedModels.CONTACT,
    LD2410Model.MOTION_SENSOR: SupportedModels.MOTION,
}

SUPPORTED_MODEL_TYPES = {
    **CONNECTABLE_SUPPORTED_MODEL_TYPES,
    **NON_CONNECTABLE_SUPPORTED_MODEL_TYPES,
}

HASS_SENSOR_TYPE_TO_LD2410_MODEL = {str(v): k for k, v in SUPPORTED_MODEL_TYPES.items()}

# Config Defaults
DEFAULT_RETRY_COUNT = 3

# Config Options
CONF_RETRY_COUNT = "retry_count"

