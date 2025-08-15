"""An abstract class common to all LD2410 entities."""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Mapping
import logging
from typing import Any, Concatenate

from .api.ld2410 import LD2410, LD2410Device
from .api.ld2410.devices.device import LD2410OperationError

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.const import ATTR_CONNECTIONS
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import ToggleEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LD2410DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class LD2410Entity(PassiveBluetoothCoordinatorEntity[LD2410DataUpdateCoordinator]):
    """Generic entity encapsulating common features of LD2410 device."""

    _device: LD2410Device
    _attr_has_entity_name = True

    def __init__(self, coordinator: LD2410DataUpdateCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device = coordinator.device
        self._last_run_success: bool | None = None
        self._address = coordinator.ble_device.address
        self._attr_unique_id = coordinator.base_unique_id
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_BLUETOOTH, self._address)},
            manufacturer=MANUFACTURER,
            model=coordinator.model,  # Sometimes the modelName is missing from the advertisement data
            name=coordinator.device_name,
        )
        if ":" not in self._address:
            # MacOS Bluetooth addresses are not mac addresses
            return
        # If the bluetooth address is also a mac address,
        # add this connection as well to prevent a new device
        # entry from being created when upgrading from a previous
        # version of the integration.
        self._attr_device_info[ATTR_CONNECTIONS].add(
            (dr.CONNECTION_NETWORK_MAC, self._address)
        )

    @property
    def parsed_data(self) -> dict[str, Any]:
        """Return parsed device data for this entity."""
        return self.coordinator.device.parsed_data

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        return {"last_run_success": self._last_run_success}

    @callback
    def _async_update_attrs(self) -> None:
        """Update the entity attributes."""

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._async_update_attrs()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(self._device.subscribe(self._handle_coordinator_update))
        return await super().async_added_to_hass()

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self._device.update()


def exception_handler[_EntityT: LD2410Entity, **_P](
    func: Callable[Concatenate[_EntityT, _P], Coroutine[Any, Any, Any]],
) -> Callable[Concatenate[_EntityT, _P], Coroutine[Any, Any, None]]:
    """Decorate LD2410 calls to handle exceptions..

    A decorator that wraps the passed in function, catches LD2410 errors.
    """

    async def handler(self: _EntityT, *args: _P.args, **kwargs: _P.kwargs) -> None:
        try:
            await func(self, *args, **kwargs)
        except LD2410OperationError as error:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="operation_error",
                translation_placeholders={"error": str(error)},
            ) from error

    return handler


class LD2410SwitchedEntity(LD2410Entity, ToggleEntity):
    """Base class for LD2410 entities that can be turned on and off."""

    _device: LD2410

    @exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn device on."""
        _LOGGER.debug("Turn LD2410 device on %s", self._address)

        self._last_run_success = bool(await self._device.turn_on())
        if self._last_run_success:
            self._attr_is_on = True
        self.async_write_ha_state()

    @exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn device off."""
        _LOGGER.debug("Turn LD2410 device off %s", self._address)

        self._last_run_success = bool(await self._device.turn_off())
        if self._last_run_success:
            self._attr_is_on = False
        self.async_write_ha_state()
