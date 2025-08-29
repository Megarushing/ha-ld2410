"""Button entities for configuration actions."""

from __future__ import annotations

import asyncio

from homeassistant.components import persistent_notification
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_call_later

try:
    from homeassistant.helpers.entity_platform import (
        AddConfigEntryEntitiesCallback,
    )
except ImportError:  # Home Assistant <2024.6
    from homeassistant.helpers.entity_platform import (
        AddEntitiesCallback as AddConfigEntryEntitiesCallback,
    )

import logging

from .const import (
    CONF_SAVED_MOVE_SENSITIVITY,
    CONF_SAVED_STILL_SENSITIVITY,
)
from .coordinator import ConfigEntryType, DataCoordinator
from .entity import Entity, exception_handler

PARALLEL_UPDATES = 0

AUTO_THRESH_DURATION = 10

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntryType,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up button entities based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            AutoSensitivityButton(coordinator),
            SaveSensitivitiesButton(coordinator, entry),
            LoadSensitivitiesButton(coordinator, entry),
        ]
    )


class AutoSensitivityButton(Entity, ButtonEntity):
    """Button to start automatic sensitivity detection."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "auto_sensitivities"

    def __init__(self, coordinator: DataCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.base_unique_id}-auto_sensitivities"

    @exception_handler
    async def async_press(self) -> None:
        """Handle the button press."""
        persistent_notification.async_create(
            self.hass,
            "Please keep the room empty for 10 seconds while calibration is in progress",
            title="LD2410",
            notification_id="ld2410_auto_sensitivities",
        )
        async_call_later(
            self.hass,
            10,
            lambda _: persistent_notification.async_dismiss(
                self.hass, "ld2410_auto_sensitivities"
            ),
        )
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


class SaveSensitivitiesButton(Entity, ButtonEntity):
    """Button to save sensitivities to config options."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "save_sensitivities"

    def __init__(self, coordinator: DataCoordinator, entry: ConfigEntryType) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{coordinator.base_unique_id}-save_sensitivities"

    @exception_handler
    async def async_press(self) -> None:
        """Handle the button press."""
        move = self.parsed_data.get("move_gate_sensitivity") or []
        still = self.parsed_data.get("still_gate_sensitivity") or []
        options = {
            **self._entry.options,
            CONF_SAVED_MOVE_SENSITIVITY: move,
            CONF_SAVED_STILL_SENSITIVITY: still,
        }
        try:
            self.coordinator.hass.config_entries.async_update_entry(
                self._entry, options=options, reload=False
            )
        except TypeError:
            self.coordinator.hass.config_entries.async_update_entry(
                self._entry, options=options
            )
        LOGGER.info("Saved gate sensitivities to config entry %s", self._entry.entry_id)
        persistent_notification.async_create(
            self.hass,
            "Sensitivities successfully saved to configurations",
            title="LD2410",
            notification_id="ld2410_save_sensitivities",
        )
        async_call_later(
            self.hass,
            10,
            lambda _: persistent_notification.async_dismiss(
                self.hass, "ld2410_save_sensitivities"
            ),
        )


class LoadSensitivitiesButton(Entity, ButtonEntity):
    """Button to load sensitivities from config options."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "load_sensitivities"

    def __init__(self, coordinator: DataCoordinator, entry: ConfigEntryType) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{coordinator.base_unique_id}-load_sensitivities"

    @exception_handler
    async def async_press(self) -> None:
        """Handle the button press."""
        move = self._entry.options.get(CONF_SAVED_MOVE_SENSITIVITY) or []
        still = self._entry.options.get(CONF_SAVED_STILL_SENSITIVITY) or []
        for gate, (m, s) in enumerate(zip(move, still)):
            await self._device.cmd_set_gate_sensitivity(gate, m, s)
        if move and still:
            self._device._fire_callbacks()
            LOGGER.info("Loaded saved gate sensitivities into device")
            persistent_notification.async_create(
                self.hass,
                "Successfully loaded previously saved gate sensitivities into the device",
                title="LD2410",
                notification_id="ld2410_load_sensitivities",
            )
            async_call_later(
                self.hass,
                10,
                lambda _: persistent_notification.async_dismiss(
                    self.hass, "ld2410_load_sensitivities"
                ),
            )
