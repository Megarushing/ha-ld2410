"""Select entities for configuration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
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

OPTIONS = ["0.75 m", "0.20 m"]
LIGHT_OPTIONS = ["off", "on"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select entities from config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [ResolutionSelect(coordinator), LightFunctionSelect(coordinator)]
    )


class ResolutionSelect(Entity, SelectEntity):
    """Representation of the distance resolution setting."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = OPTIONS
    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:tape-measure"
    _attr_translation_key = "distance_resolution"

    def __init__(self, coordinator: DataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-resolution"

    @property
    def current_option(self) -> str | None:
        idx = self.parsed_data.get("resolution")
        if idx is None or idx >= len(self.options):
            return None
        return self.options[idx]

    @exception_handler
    async def async_select_option(self, option: str) -> None:
        index = self.options.index(option)
        await self._device.cmd_set_resolution(index)


class LightFunctionSelect(Entity, SelectEntity):
    """Representation of light function on/off."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = LIGHT_OPTIONS
    _attr_entity_registry_enabled_default = True
    _attr_icon = "mdi:lightbulb"
    _attr_translation_key = "light_function"

    def __init__(self, coordinator: DataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-light_function"

    @property
    def current_option(self) -> str | None:
        enabled = self.parsed_data.get("light_function")
        if enabled is None:
            return None
        return "on" if enabled else "off"

    @exception_handler
    async def async_select_option(self, option: str) -> None:
        await self._device.cmd_set_light_function(option == "on")
