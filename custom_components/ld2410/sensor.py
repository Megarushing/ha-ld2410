"""Support for sensors."""

from __future__ import annotations

from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfLength,
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

from .coordinator import ConfigEntryType, DataCoordinator
from .entity import Entity

PARALLEL_UPDATES = 0

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    "rssi": SensorEntityDescription(
        key="rssi",
        translation_key="bluetooth_signal",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "firmware_version": SensorEntityDescription(
        key="firmware_version",
        name="Firmware version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "firmware_build_date": SensorEntityDescription(
        key="firmware_build_date",
        name="Firmware build date",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}

for key, t_key, unit in (
    ("move_distance_cm", "move_distance", UnitOfLength.CENTIMETERS),
    ("move_energy", "move_energy", PERCENTAGE),
    ("still_distance_cm", "still_distance", UnitOfLength.CENTIMETERS),
    ("still_energy", "still_energy", PERCENTAGE),
    ("detect_distance_cm", "detect_distance", UnitOfLength.CENTIMETERS),
    ("max_move_gate", "max_move_gate", None),
    ("max_still_gate", "max_still_gate", None),
):
    SENSOR_TYPES[key] = SensorEntityDescription(
        key=key,
        translation_key=t_key,
        native_unit_of_measurement=unit,
        state_class=SensorStateClass.MEASUREMENT,
    )

for gate in range(9):
    SENSOR_TYPES.update(
        {
            f"move_gate_energy_{gate}": SensorEntityDescription(
                key=f"move_gate_energy_{gate}",
                name=f"Moving gate {gate} energy",
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                entity_registry_enabled_default=False,
            ),
            f"still_gate_energy_{gate}": SensorEntityDescription(
                key=f"still_gate_energy_{gate}",
                name=f"Still gate {gate} energy",
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                entity_registry_enabled_default=False,
            ),
        }
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors based on a config entry."""
    coordinator = entry.runtime_data
    entities = [
        Sensor(coordinator, sensor)
        for sensor in coordinator.device.parsed_data
        if sensor in SENSOR_TYPES and sensor != "rssi"
    ]
    entities.append(RSSISensor(coordinator, "rssi"))
    async_add_entities(entities)


class Sensor(Entity, SensorEntity):
    """Representation of a sensor."""

    def __init__(
        self,
        coordinator: DataCoordinator,
        sensor: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor = sensor
        self._attr_unique_id = f"{coordinator.base_unique_id}-{sensor}"
        self.entity_description = SENSOR_TYPES[sensor]

    @property
    def native_value(self) -> str | int | None:
        """Return the state of the sensor."""
        return self.parsed_data[self._sensor]


class RSSISensor(Sensor):
    """Representation of a RSSI sensor."""

    @property
    def native_value(self) -> str | int | None:
        """Return the state of the sensor."""
        # The device supports both connectable and non-connectable devices
        # so we need to request the rssi value based on the connectable instead
        # of the nearest scanner since that is the RSSI that matters for controlling
        # the device.
        if service_info := async_last_service_info(
            self.hass, self._address, self.coordinator.connectable
        ):
            return service_info.rssi
        return None
