"""Support for LD2410 binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant

try:
    from homeassistant.helpers.entity_platform import (
        AddConfigEntryEntitiesCallback,
    )
except ImportError:  # Home Assistant <2024.6
    from homeassistant.helpers.entity_platform import (
        AddEntitiesCallback as AddConfigEntryEntitiesCallback,
    )

from .coordinator import LD2410ConfigEntry, LD2410DataUpdateCoordinator
from .entity import LD2410Entity

PARALLEL_UPDATES = 0

BINARY_SENSOR_TYPES: dict[str, BinarySensorEntityDescription] = {
    "motion_detected": BinarySensorEntityDescription(
        key="pir_state",
        name=None,
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    "presence_detected": BinarySensorEntityDescription(
        key="presence_state",
        name=None,
        device_class=BinarySensorDeviceClass.PRESENCE,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LD2410ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LD2410 curtain based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        LD2410BinarySensor(coordinator, binary_sensor)
        for binary_sensor in coordinator.device.parsed_data
        if binary_sensor in BINARY_SENSOR_TYPES
    )


class LD2410BinarySensor(LD2410Entity, BinarySensorEntity):
    """Representation of a LD2410 binary sensor."""

    def __init__(
        self,
        coordinator: LD2410DataUpdateCoordinator,
        binary_sensor: str,
    ) -> None:
        """Initialize the LD2410 sensor."""
        super().__init__(coordinator)
        self._sensor = binary_sensor
        self._attr_unique_id = f"{coordinator.base_unique_id}-{binary_sensor}"
        self.entity_description = BINARY_SENSOR_TYPES[binary_sensor]

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        return self.parsed_data[self._sensor]
