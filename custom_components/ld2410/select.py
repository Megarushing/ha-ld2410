"""Select entities for baud rate configuration."""

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

BAUD_OPTIONS = [
    "9600",
    "19200",
    "38400",
    "57600",
    "115200",
    "230400",
    "256000",
    "460800",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select entities for a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([BaudRateSelect(coordinator)])


class BaudRateSelect(Entity, SelectEntity):
    """Representation of the baud rate configuration select."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Baud rate"
    _attr_options = BAUD_OPTIONS

    def __init__(self, coordinator: DataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-baud_rate"

    @property
    def current_option(self) -> str | None:
        value = self.parsed_data.get("baud_rate")
        return str(value) if value is not None else None

    @exception_handler
    async def async_select_option(self, option: str) -> None:
        await self._device.cmd_set_baud_rate(int(option))
