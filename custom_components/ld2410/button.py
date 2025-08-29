"""Button entities for configuration actions."""

from __future__ import annotations

import asyncio
import inspect

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

from .const import CONF_MOVE_THRESHOLDS, CONF_STILL_THRESHOLDS
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
    async_add_entities(
        [
            AutoThresholdButton(coordinator),
            SaveThresholdsButton(coordinator, entry),
            LoadThresholdsButton(coordinator, entry),
        ]
    )


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
        await asyncio.sleep(AUTO_THRESH_DURATION)
        while await self._device.cmd_query_auto_thresholds() != 0:
            await asyncio.sleep(1)
        params = await self._device.cmd_read_params()
        if self._device._update_parsed_data(
            {
                "move_gate_sensitivity": params.get("move_gate_sensitivity"),
                "still_gate_sensitivity": params.get("still_gate_sensitivity"),
            }
        ):
            self._device._fire_callbacks()


class SaveThresholdsButton(Entity, ButtonEntity):
    """Button to save thresholds to config entry options."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "save_thresholds"

    def __init__(self, coordinator: DataCoordinator, entry: ConfigEntryType) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{coordinator.base_unique_id}-save_thresholds"

    async def async_press(self) -> None:
        """Handle the button press."""
        move = list(self.parsed_data.get("move_gate_sensitivity", []))
        still = list(self.parsed_data.get("still_gate_sensitivity", []))
        update_entry = self.hass.config_entries.async_update_entry
        kwargs = {
            "options": {
                **self._entry.options,
                CONF_MOVE_THRESHOLDS: move,
                CONF_STILL_THRESHOLDS: still,
            }
        }
        params = inspect.signature(update_entry).parameters
        if "update_listeners" in params:
            kwargs["update_listeners"] = False
        elif "reload" in params:
            kwargs["reload"] = False
        update_entry(self._entry, **kwargs)


class LoadThresholdsButton(Entity, ButtonEntity):
    """Button to load thresholds from options to the device."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "load_thresholds"

    def __init__(self, coordinator: DataCoordinator, entry: ConfigEntryType) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{coordinator.base_unique_id}-load_thresholds"

    @exception_handler
    async def async_press(self) -> None:
        """Handle the button press."""
        move = self._entry.options.get(CONF_MOVE_THRESHOLDS)
        still = self._entry.options.get(CONF_STILL_THRESHOLDS)
        if not move or not still:
            return
        for gate in range(min(len(move), len(still))):
            await self._device.cmd_set_gate_sensitivity(gate, move[gate], still[gate])
        self._device._fire_callbacks()
