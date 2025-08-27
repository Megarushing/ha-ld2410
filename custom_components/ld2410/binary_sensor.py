"""Support for binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory

try:
    from homeassistant.helpers.entity_platform import (
        AddConfigEntryEntitiesCallback,
    )
except ImportError:  # Home Assistant <2024.6
    from homeassistant.helpers.entity_platform import (
        AddEntitiesCallback as AddConfigEntryEntitiesCallback,
    )

from .coordinator import ConfigEntryType, DataCoordinator
from .entity import Entity

PARALLEL_UPDATES = 0

BINARY_SENSOR_TYPES: dict[str, BinarySensorEntityDescription] = {
    "motion": BinarySensorEntityDescription(
        key="moving",
        name="Motion",
        device_class=BinarySensorDeviceClass.MOVING,
        entity_registry_enabled_default=True,
    ),
    "static": BinarySensorEntityDescription(
        key="stationary",
        name="Static",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        entity_registry_enabled_default=True,
    ),
    "occupancy": BinarySensorEntityDescription(
        key="occupancy",
        name="Occupancy",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        entity_registry_enabled_default=True,
    ),
    "out_pin": BinarySensorEntityDescription(
        key="out_pin",
        name="OUT pin",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        BinarySensor(coordinator, binary_sensor)
        for binary_sensor in BINARY_SENSOR_TYPES
    )


class BinarySensor(Entity, BinarySensorEntity):
    """Representation of a binary sensor."""

    def __init__(
        self,
        coordinator: DataCoordinator,
        binary_sensor: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor = binary_sensor
        self._attr_unique_id = f"{coordinator.base_unique_id}-{binary_sensor}"
        self.entity_description = BINARY_SENSOR_TYPES[binary_sensor]

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        return bool(self.parsed_data.get(self.entity_description.key))
