"""Support for LD2410 bot."""

from __future__ import annotations

from typing import Any

from .api import ld2410

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import LD2410ConfigEntry, LD2410DataUpdateCoordinator
from .entity import LD2410SwitchedEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LD2410ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LD2410 based on a config entry."""
    async_add_entities([LD2410Switch(entry.runtime_data)])


class LD2410Switch(LD2410SwitchedEntity, SwitchEntity, RestoreEntity):
    """Representation of a LD2410 switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_translation_key = "bot"
    _attr_name = None
    _device: ld2410.LD2410

    def __init__(self, coordinator: LD2410DataUpdateCoordinator) -> None:
        """Initialize the LD2410."""
        super().__init__(coordinator)
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        if not (last_state := await self.async_get_last_state()):
            return
        self._attr_is_on = last_state.state == STATE_ON
        self._last_run_success = last_state.attributes.get("last_run_success")

    @property
    def assumed_state(self) -> bool:
        """Return true if unable to access real state of entity."""
        return not self._device.switch_mode()

    @property
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        if not self._device.switch_mode():
            return self._attr_is_on
        return self._device.is_on()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            **super().extra_state_attributes,
            "switch_mode": self._device.switch_mode(),
        }
