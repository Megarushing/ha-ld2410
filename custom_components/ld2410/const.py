"""Constants for the integration."""

from enum import StrEnum

from .api import Model

DOMAIN = "ld2410"
MANUFACTURER = "ld2410"

# Config Attributes

DEFAULT_NAME = "LD2410"


class SupportedModels(StrEnum):
    """Supported models."""

    LD2410 = "ld2410"


CONNECTABLE_MODEL_TYPES: dict[Model, SupportedModels] = {
    Model.LD2410: SupportedModels.LD2410,
}

SUPPORTED_MODEL_TYPES = CONNECTABLE_MODEL_TYPES

HASS_SENSOR_TYPE_TO_MODEL = {str(v): k for k, v in CONNECTABLE_MODEL_TYPES.items()}

# Config Defaults
DEFAULT_RETRY_COUNT = 3

# Config Options
CONF_RETRY_COUNT = "retry_count"
CONF_SAVED_MOVE_SENSITIVITY = "saved_move_gate_sensitivity"
CONF_SAVED_STILL_SENSITIVITY = "saved_still_gate_sensitivity"
