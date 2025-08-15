"""Support for LD2410 curtains."""

from __future__ import annotations

import logging
from typing import Any

from .api import ld2410

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import LD2410ConfigEntry, LD2410DataUpdateCoordinator
from .entity import LD2410Entity, exception_handler

# Initialize the logger
_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LD2410ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LD2410 curtain based on a config entry."""
    coordinator = entry.runtime_data
    if isinstance(coordinator.device, ld2410.LD2410BlindTilt):
        async_add_entities([LD2410BlindTiltEntity(coordinator)])
    elif isinstance(coordinator.device, ld2410.LD2410RollerShade):
        async_add_entities([LD2410RollerShadeEntity(coordinator)])
    else:
        async_add_entities([LD2410CurtainEntity(coordinator)])


class LD2410CurtainEntity(LD2410Entity, CoverEntity, RestoreEntity):
    """Representation of a LD2410."""

    _device: ld2410.LD2410Curtain
    _attr_device_class = CoverDeviceClass.CURTAIN
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )
    _attr_translation_key = "cover"
    _attr_name = None

    def __init__(self, coordinator: LD2410DataUpdateCoordinator) -> None:
        """Initialize the LD2410."""
        super().__init__(coordinator)
        self._attr_is_closed = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state or ATTR_CURRENT_POSITION not in last_state.attributes:
            return

        self._attr_current_cover_position = last_state.attributes.get(
            ATTR_CURRENT_POSITION
        )
        self._last_run_success = last_state.attributes.get("last_run_success")
        if self._attr_current_cover_position is not None:
            self._attr_is_closed = self._attr_current_cover_position <= 20

    @exception_handler
    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the curtain."""

        _LOGGER.debug("LD2410 to open curtain %s", self._address)
        self._last_run_success = bool(await self._device.open())
        self._attr_is_opening = self._device.is_opening()
        self._attr_is_closing = self._device.is_closing()
        self.async_write_ha_state()

    @exception_handler
    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the curtain."""

        _LOGGER.debug("LD2410 to close the curtain %s", self._address)
        self._last_run_success = bool(await self._device.close())
        self._attr_is_opening = self._device.is_opening()
        self._attr_is_closing = self._device.is_closing()
        self.async_write_ha_state()

    @exception_handler
    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the moving of this device."""

        _LOGGER.debug("LD2410 to stop %s", self._address)
        self._last_run_success = bool(await self._device.stop())
        self._attr_is_opening = self._device.is_opening()
        self._attr_is_closing = self._device.is_closing()
        self.async_write_ha_state()

    @exception_handler
    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover shutter to a specific position."""
        position = kwargs.get(ATTR_POSITION)

        _LOGGER.debug("LD2410 to move at %d %s", position, self._address)
        self._last_run_success = bool(await self._device.set_position(position))
        self._attr_is_opening = self._device.is_opening()
        self._attr_is_closing = self._device.is_closing()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_closing = self._device.is_closing()
        self._attr_is_opening = self._device.is_opening()
        self._attr_current_cover_position = self.parsed_data["position"]
        self._attr_is_closed = self.parsed_data["position"] <= 20

        self.async_write_ha_state()


class LD2410BlindTiltEntity(LD2410Entity, CoverEntity, RestoreEntity):
    """Representation of a LD2410."""

    _device: ld2410.LD2410BlindTilt
    _attr_device_class = CoverDeviceClass.BLIND
    _attr_supported_features = (
        CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
        | CoverEntityFeature.STOP_TILT
        | CoverEntityFeature.SET_TILT_POSITION
    )
    _attr_name = None
    _attr_translation_key = "cover"
    CLOSED_UP_THRESHOLD = 80
    CLOSED_DOWN_THRESHOLD = 20

    def __init__(self, coordinator: LD2410DataUpdateCoordinator) -> None:
        """Initialize the LD2410."""
        super().__init__(coordinator)
        self._attr_is_closed = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state or ATTR_CURRENT_TILT_POSITION not in last_state.attributes:
            return

        self._attr_current_cover_tilt_position = last_state.attributes.get(
            ATTR_CURRENT_TILT_POSITION
        )
        self._last_run_success = last_state.attributes.get("last_run_success")
        if (_tilt := self._attr_current_cover_tilt_position) is not None:
            self._attr_is_closed = (_tilt < self.CLOSED_DOWN_THRESHOLD) or (
                _tilt > self.CLOSED_UP_THRESHOLD
            )

    @exception_handler
    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the tilt."""

        _LOGGER.debug("LD2410 to open blind tilt %s", self._address)
        self._last_run_success = bool(await self._device.open())
        self.async_write_ha_state()

    @exception_handler
    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the tilt."""

        _LOGGER.debug("LD2410 to close the blind tilt %s", self._address)
        self._last_run_success = bool(await self._device.close())
        self.async_write_ha_state()

    @exception_handler
    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop the moving of this device."""

        _LOGGER.debug("LD2410 to stop %s", self._address)
        self._last_run_success = bool(await self._device.stop())
        self.async_write_ha_state()

    @exception_handler
    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        position = kwargs.get(ATTR_TILT_POSITION)

        _LOGGER.debug("LD2410 to move at %d %s", position, self._address)
        self._last_run_success = bool(await self._device.set_position(position))
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _tilt = self.parsed_data["tilt"]
        self._attr_current_cover_tilt_position = _tilt
        self._attr_is_closed = (_tilt < self.CLOSED_DOWN_THRESHOLD) or (
            _tilt > self.CLOSED_UP_THRESHOLD
        )
        self._attr_is_opening = self.parsed_data["motionDirection"]["opening"]
        self._attr_is_closing = self.parsed_data["motionDirection"]["closing"]
        self.async_write_ha_state()


class LD2410RollerShadeEntity(LD2410Entity, CoverEntity, RestoreEntity):
    """Representation of a LD2410."""

    _device: ld2410.LD2410RollerShade
    _attr_device_class = CoverDeviceClass.SHADE
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    _attr_translation_key = "cover"
    _attr_name = None

    def __init__(self, coordinator: LD2410DataUpdateCoordinator) -> None:
        """Initialize the ld2410."""
        super().__init__(coordinator)
        self._attr_is_closed = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state or ATTR_CURRENT_POSITION not in last_state.attributes:
            return

        self._attr_current_cover_position = last_state.attributes.get(
            ATTR_CURRENT_POSITION
        )
        self._last_run_success = last_state.attributes.get("last_run_success")
        if self._attr_current_cover_position is not None:
            self._attr_is_closed = self._attr_current_cover_position <= 20

    @exception_handler
    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the roller shade."""

        _LOGGER.debug("LD2410 to open roller shade %s", self._address)
        self._last_run_success = bool(await self._device.open())
        self._attr_is_opening = self._device.is_opening()
        self._attr_is_closing = self._device.is_closing()
        self.async_write_ha_state()

    @exception_handler
    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the roller shade."""

        _LOGGER.debug("LD2410 to close roller shade %s", self._address)
        self._last_run_success = bool(await self._device.close())
        self._attr_is_opening = self._device.is_opening()
        self._attr_is_closing = self._device.is_closing()
        self.async_write_ha_state()

    @exception_handler
    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the moving of roller shade."""

        _LOGGER.debug("LD2410 to stop roller shade %s", self._address)
        self._last_run_success = bool(await self._device.stop())
        self._attr_is_opening = self._device.is_opening()
        self._attr_is_closing = self._device.is_closing()
        self.async_write_ha_state()

    @exception_handler
    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""

        position = kwargs.get(ATTR_POSITION)
        _LOGGER.debug("LD2410 to move at %d %s", position, self._address)
        self._last_run_success = bool(await self._device.set_position(position))
        self._attr_is_opening = self._device.is_opening()
        self._attr_is_closing = self._device.is_closing()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_closing = self._device.is_closing()
        self._attr_is_opening = self._device.is_opening()
        self._attr_current_cover_position = self.parsed_data["position"]
        self._attr_is_closed = self.parsed_data["position"] <= 20

        self.async_write_ha_state()
