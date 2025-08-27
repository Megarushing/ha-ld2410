"""Button entities for configuration actions."""

from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity
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

AUTO_THRESH_DURATION = 10


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up button entities based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([AutoThresholdButton(coordinator)])


class AutoThresholdButton(Entity, ButtonEntity):
    """Button to start automatic threshold detection."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "auto_threshold"

    def __init__(self, coordinator: DataCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-auto_threshold"

    @exception_handler
    async def async_press(self) -> None:
        """Handle the button press."""
        await self._device.cmd_auto_thresholds(AUTO_THRESH_DURATION)
        while True:
            await asyncio.sleep(1)
            if await self._device.cmd_query_auto_thresholds() == 0:
                break
        params = await self._device.cmd_read_params()
        if self._device._update_parsed_data(
            {
                "move_gate_sensitivity": params.get("move_gate_sensitivity"),
                "still_gate_sensitivity": params.get("still_gate_sensitivity"),
            }
        ):
            self._device._fire_callbacks()
