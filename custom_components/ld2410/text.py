"""Text entity for changing bluetooth password."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
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
from .entity import Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up text entities based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([NewPasswordText(coordinator)])


class NewPasswordText(Entity, TextEntity):
    """Text field for providing a new bluetooth password."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "new_password"
    _attr_mode = TextMode.TEXT
    _attr_pattern = r"^[ -~]*$"

    def __init__(self, coordinator: DataCoordinator) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-new_password"
        coordinator.new_password = ""

    @property
    def native_value(self) -> str | None:
        """Return the current value."""
        return getattr(self.coordinator, "new_password", "")

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        self.coordinator.new_password = value
        self.async_write_ha_state()
