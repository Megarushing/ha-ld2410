"""Support for devices."""

import asyncio
import contextlib
import logging

from . import api

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSOR_TYPE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_RETRY_COUNT,
    CONNECTABLE_MODEL_TYPES,
    DEFAULT_RETRY_COUNT,
    CONF_SAVED_MOVE_SENSITIVITY,
    CONF_SAVED_STILL_SENSITIVITY,
    DOMAIN,
    HASS_SENSOR_TYPE_TO_MODEL,
    SupportedModels,
)
from .coordinator import ConfigEntryType, DataCoordinator


async def _async_try_connect(device: api.Device) -> None:
    """Attempt background connection; suppress failures in setup context."""
    with contextlib.suppress(Exception):
        await device._ensure_connected()

PLATFORMS_BY_TYPE = {
    SupportedModels.LD2410.value: [
        Platform.BINARY_SENSOR,
        Platform.SENSOR,
        Platform.BUTTON,
        Platform.NUMBER,
        Platform.SELECT,
        Platform.TEXT,
    ],
}
CLASS_BY_DEVICE = {SupportedModels.LD2410.value: api.LD2410}


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntryType) -> bool:
    """Set up the device from a config entry."""
    assert entry.unique_id is not None
    if CONF_ADDRESS not in entry.data and CONF_MAC in entry.data:
        # Bleak uses addresses not mac addresses which are actually
        # UUIDs on some platforms (MacOS).
        mac = entry.data[CONF_MAC]
        if "-" not in mac:
            mac = dr.format_mac(mac)
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_ADDRESS: mac},
        )

    if not entry.options:
        hass.config_entries.async_update_entry(
            entry,
            options={CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT},
        )

    sensor_type: str = entry.data[CONF_SENSOR_TYPE]
    model = HASS_SENSOR_TYPE_TO_MODEL.get(sensor_type, api.Model.LD2410)
    # connectable means we can make connections to the device
    connectable = model in CONNECTABLE_MODEL_TYPES
    address: str = entry.data[CONF_ADDRESS]

    await api.close_stale_connections_by_address(address)

    ble_device = bluetooth.async_ble_device_from_address(
        hass, address.upper(), connectable
    )
    if not ble_device:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="device_not_found_error",
            translation_placeholders={"sensor_type": sensor_type, "address": address},
        )

    cls = CLASS_BY_DEVICE.get(sensor_type, api.Device)
    try:
        device = cls(
            device=ble_device,
            password=entry.data.get(CONF_PASSWORD),
            retry_count=entry.options[CONF_RETRY_COUNT],
        )
    except ValueError as err:
        _LOGGER.error(
            "Device initialization failed because of incorrect configuration parameters: %s",
            err,
        )
        return False

    # Start establishing a connection in the background to provoke retries
    # and initial authorization, but do not await it to avoid blocking setup.
    hass.async_create_task(_async_try_connect(device))

    data_coordinator = entry.runtime_data = DataCoordinator(
        hass,
        _LOGGER,
        ble_device,
        device,
        entry.unique_id,
        entry.data.get(CONF_NAME, entry.title),
        connectable,
        model,
    )
    data_coordinator.options = dict(entry.options)
    entry.async_on_unload(data_coordinator.async_start())

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS_BY_TYPE[sensor_type]
    )

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator: DataCoordinator = entry.runtime_data
    new_options = dict(entry.options)
    allowed = {CONF_SAVED_MOVE_SENSITIVITY, CONF_SAVED_STILL_SENSITIVITY}
    previous = getattr(coordinator, "options", {})
    coordinator.options = new_options
    if {k: v for k, v in previous.items() if k not in allowed} == {
        k: v for k, v in new_options.items() if k not in allowed
    }:
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    sensor_type = entry.data[CONF_SENSOR_TYPE]
    device = entry.runtime_data.device
    device._should_reconnect = False
    device._cancel_disconnect_timer()
    if device._restart_connection_tasks:
        for task in device._restart_connection_tasks:
            task.cancel()
        for task in device._restart_connection_tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        device._restart_connection_tasks.clear()
    if device._timed_disconnect_task:
        device._timed_disconnect_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await device._timed_disconnect_task
        device._timed_disconnect_task = None
    await device.async_disconnect()
    return await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS_BY_TYPE[sensor_type]
    )
