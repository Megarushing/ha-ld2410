"""Support for devices."""

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
    DOMAIN,
    HASS_SENSOR_TYPE_TO_MODEL,
    SupportedModels,
)
from .coordinator import ConfigEntryType, DataCoordinator

PLATFORMS_BY_TYPE = {
    SupportedModels.LD2410.value: [Platform.BINARY_SENSOR, Platform.SENSOR],
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

    if entry.data.get(CONF_PASSWORD):
        await device.cmd_send_bluetooth_password()

    coordinator = entry.runtime_data = DataCoordinator(
        hass,
        _LOGGER,
        ble_device,
        device,
        entry.unique_id,
        entry.data.get(CONF_NAME, entry.title),
        connectable,
        model,
    )
    entry.async_on_unload(coordinator.async_start())
    if not await coordinator.async_wait_ready():
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="advertising_state_error",
            translation_placeholders={"address": address},
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS_BY_TYPE[sensor_type]
    )

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    sensor_type = entry.data[CONF_SENSOR_TYPE]
    await entry.runtime_data.device.async_disconnect()
    return await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS_BY_TYPE[sensor_type]
    )
