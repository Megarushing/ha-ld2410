"""Number entities for gate sensitivities."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
        move_values = self.parsed_data.get("move_gate_sensitivity") or []
        still_values = self.parsed_data.get("still_gate_sensitivity") or []
        move = move_values[self._gate] if self._gate < len(move_values) else 0
        still = still_values[self._gate] if self._gate < len(still_values) else 0
        if self._data_key == "move_gate_sensitivity":
            move = int(value)
        else:
            still = int(value)
        await self._device.cmd_set_gate_sensitivity(self._gate, move, still)
