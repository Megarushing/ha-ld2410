"""Support for sensors."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

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
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "firmware_version": SensorEntityDescription(
        key="firmware_version",
        name="Firmware version",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "firmware_build_date": SensorEntityDescription(
        key="firmware_build_date",
        name="Firmware build date",
        entity_registry_enabled_default=True,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "type": SensorEntityDescription(
        key="type",
        name="Frame type",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "move_distance": SensorEntityDescription(
        key="move_distance_cm",
        name="Moving distance",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "move_energy": SensorEntityDescription(
        key="move_energy",
        name="Moving energy",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "still_distance": SensorEntityDescription(
        key="still_distance_cm",
        name="Still distance",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "still_energy": SensorEntityDescription(
        key="still_energy",
        name="Still energy",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "detect_distance": SensorEntityDescription(
        key="detect_distance_cm",
        name="Detect distance",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "max_move_gate": SensorEntityDescription(
        key="max_move_gate",
        name="Max motion gate",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "max_still_gate": SensorEntityDescription(
        key="max_still_gate",
        name="Max still gate",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "photo_sensor": SensorEntityDescription(
        key="photo_sensor",
        name="Photo sensor",
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ILLUMINANCE,
        entity_registry_enabled_default=False,
    ),
    "last_frame": SensorEntityDescription(
        key="last_frame",
        translation_key="last_frame",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors based on a config entry."""
    coordinator = entry.runtime_data
    polled = ("rssi", "last_frame")
    entities = [
        Sensor(coordinator, sensor) for sensor in SENSOR_TYPES if sensor not in polled
    ]
    entities.append(RSSISensor(coordinator, "rssi"))
    entities.append(LastFrameSensor(coordinator, "last_frame"))
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
        prefix = "Motion" if data_key == "move_gate_energy" else "Still"
        self.entity_description = SensorEntityDescription(
            key=f"{data_key}_{gate}",
            name=f"{prefix} gate {gate} energy",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
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

    _attr_should_poll = True

    async def async_update(self) -> None:
        await self._device.read_rssi()

    @property
    def native_value(self) -> str | int | None:
        """Return the state of the sensor."""
        rssi = self._device.rssi
        return None if rssi == -127 else rssi


class LastFrameSensor(Sensor):
    """Representation of the last uplink frame timestamp.

    Diagnostic probe for a stalled uplink stream. Polled rather than
    callback-driven because callbacks only fire when frame *content* changes,
    which is exactly what a stalled stream and an empty room have in common.
    """

    _attr_should_poll = True

    async def async_update(self) -> None:
        """Refresh on the poll interval; the value is read in native_value."""

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        timestamp = self._device.last_frame_time
        return None if timestamp is None else dt_util.utc_from_timestamp(timestamp)
