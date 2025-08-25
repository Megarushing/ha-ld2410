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
    "move_distance": SensorEntityDescription(
        key="move_distance_cm",
        name="Moving distance",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "move_energy": SensorEntityDescription(
        key="move_energy",
        name="Moving energy",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "still_distance": SensorEntityDescription(
        key="still_distance_cm",
        name="Still distance",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "still_energy": SensorEntityDescription(
        key="still_energy",
        name="Still energy",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "detect_distance": SensorEntityDescription(
        key="detect_distance_cm",
        name="Detect distance",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "max_move_gate": SensorEntityDescription(
        key="max_move_gate",
        name="Max moving gate",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "max_still_gate": SensorEntityDescription(
        key="max_still_gate",
        name="Max still gate",
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors based on a config entry."""
    coordinator = entry.runtime_data
    entities = [
        Sensor(coordinator, sensor) for sensor in SENSOR_TYPES if sensor != "rssi"
    ]
    entities.append(RSSISensor(coordinator, "rssi"))
    for key in ("move_gate_energy", "still_gate_energy"):
        for gate in range(9):
            entities.append(GateEnergySensor(coordinator, key, gate))
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
        return self.parsed_data.get(self.entity_description.key)


class GateEnergySensor(Entity, SensorEntity):
    """Representation of a gate energy sensor."""

    def __init__(
        self,
        coordinator: DataCoordinator,
        data_key: str,
        gate: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._data_key = data_key
        self._gate = gate
        prefix = "Moving" if data_key == "move_gate_energy" else "Still"
        self.entity_description = SensorEntityDescription(
            key=f"{data_key}_{gate}",
            name=f"{prefix} gate {gate} energy",
            state_class=SensorStateClass.MEASUREMENT,
        )
        self._attr_unique_id = f"{coordinator.base_unique_id}-{data_key}-{gate}"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        values = self.parsed_data.get(self._data_key)
        if values is None or len(values) <= self._gate:
            return None
        return values[self._gate]


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
