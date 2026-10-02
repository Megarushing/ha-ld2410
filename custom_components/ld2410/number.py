"""Number entities for gate sensitivities."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

try:
    from homeassistant.helpers.entity_platform import (
        AddConfigEntryEntitiesCallback,
    )
except ImportError:  # Home Assistant <2024.6
    from homeassistant.helpers.entity_platform import (
        AddEntitiesCallback as AddConfigEntryEntitiesCallback,
    )

from .coordinator import ConfigEntryType, DataCoordinator
from .entity import Entity, exception_handler

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up number entities from config entry."""
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = []
    for gate in range(9):
        entities.append(
            GateSensitivityNumber(coordinator, "move_gate_sensitivity", gate)
        )
        entities.append(
            GateSensitivityNumber(coordinator, "still_gate_sensitivity", gate)
        )
    entities.append(AbsenceDelayNumber(coordinator))
    entities.append(MaxGateNumber(coordinator, "max_move_gate"))
    entities.append(MaxGateNumber(coordinator, "max_still_gate"))
    entities.append(LightSensitivityNumber(coordinator))
    async_add_entities(entities)


class GateSensitivityNumber(Entity, NumberEntity):
    """Representation of a gate sensitivity slider."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: DataCoordinator, data_key: str, gate: int) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._gate = gate
        prefix = "M" if data_key == "move_gate_sensitivity" else "S"
        self._attr_name = f"{prefix}G{gate} Sensitivity"
        self._attr_unique_id = f"{coordinator.base_unique_id}-{data_key}-{gate}"

    @property
    def native_value(self) -> int | None:
        values = self.parsed_data.get(self._data_key)
        if values is None or len(values) <= self._gate:
            return None
        return values[self._gate]

    @exception_handler
    async def async_set_native_value(self, value: float) -> None:
        # Send only this value; the device layer fills in the paired one.
        if self._data_key == "move_gate_sensitivity":
            await self._device.cmd_set_gate_sensitivity(self._gate, move=int(value))
        else:
            await self._device.cmd_set_gate_sensitivity(self._gate, still=int(value))


class AbsenceDelayNumber(Entity, NumberEntity):
    """Representation of the absence delay configuration."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 65535
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator: DataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Absence delay"
        self._attr_unique_id = f"{coordinator.base_unique_id}-absence_delay"

    @property
    def native_value(self) -> int | None:
        return self.parsed_data.get("absence_delay")

    @exception_handler
    async def async_set_native_value(self, value: float) -> None:
        await self._device.cmd_set_absence_delay(int(value))


class MaxGateNumber(Entity, NumberEntity):
    """Farthest gate that detects motion or presence; limits the range."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 2
    _attr_native_max_value = 8
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataCoordinator, data_key: str) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_translation_key = data_key
        self._attr_unique_id = f"{coordinator.base_unique_id}-{data_key}-number"

    @property
    def native_value(self) -> int | None:
        return self.parsed_data.get(self._data_key)

    @exception_handler
    async def async_set_native_value(self, value: float) -> None:
        if self._data_key == "max_move_gate":
            await self._device.cmd_set_max_gates(move_gate=int(value))
        else:
            await self._device.cmd_set_max_gates(still_gate=int(value))


class LightSensitivityNumber(Entity, NumberEntity):
    """Representation of light sensitivity slider."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 255
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:brightness-6"
    _attr_translation_key = "light_sensitivity"

    def __init__(self, coordinator: DataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-light_sensitivity"

    @property
    def native_value(self) -> int | None:
        return self.parsed_data.get("light_threshold")

    @exception_handler
    async def async_set_native_value(self, value: float) -> None:
        await self._device.cmd_set_light_config(threshold=int(value))
