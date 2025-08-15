"""LD2410 integration light platform."""

from __future__ import annotations

import logging
from typing import Any, cast

from .api import ld2410
from .api.ld2410 import ColorMode as LD2410ColorMode

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LD2410ConfigEntry
from .entity import LD2410Entity, exception_handler

LD2410_COLOR_MODE_TO_HASS = {
    LD2410ColorMode.RGB: ColorMode.RGB,
    LD2410ColorMode.COLOR_TEMP: ColorMode.COLOR_TEMP,
}

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LD2410ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the ld2410 light."""
    async_add_entities([LD2410LightEntity(entry.runtime_data)])


class LD2410LightEntity(LD2410Entity, LightEntity):
    """Representation of ld2410 light bulb."""

    _device: ld2410.LD2410BaseLight
    _attr_name = None
    _attr_translation_key = "light"

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return the max color temperature."""
        return self._device.max_temp

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return the min color temperature."""
        return self._device.min_temp

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {LD2410_COLOR_MODE_TO_HASS[mode] for mode in self._device.color_modes}

    @property
    def supported_features(self) -> LightEntityFeature:
        """Return the supported features."""
        return LightEntityFeature.EFFECT if self.effect_list else LightEntityFeature(0)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        return max(0, min(255, round(self._device.brightness * 2.55)))

    @property
    def color_mode(self) -> ColorMode | None:
        """Return the color mode of the light."""
        return LD2410_COLOR_MODE_TO_HASS.get(self._device.color_mode, ColorMode.UNKNOWN)

    @property
    def effect_list(self) -> list[str] | None:
        """Return the list of effects supported by the light."""
        return self._device.get_effect_list

    @property
    def effect(self) -> str | None:
        """Return the current effect of the light."""
        return self._device.get_effect()

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color of the light."""
        return self._device.rgb

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature of the light."""
        return self._device.color_temp

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._device.on

    @exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        _LOGGER.debug("Turning on light %s, address %s", kwargs, self._address)
        brightness = round(
            cast(int, kwargs.get(ATTR_BRIGHTNESS, self.brightness)) / 255 * 100
        )

        if (
            self.supported_color_modes
            and ColorMode.COLOR_TEMP in self.supported_color_modes
            and ATTR_COLOR_TEMP_KELVIN in kwargs
        ):
            kelvin = max(2700, min(6500, kwargs[ATTR_COLOR_TEMP_KELVIN]))
            await self._device.set_color_temp(brightness, kelvin)
            return
        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            await self._device.set_effect(effect)
            return
        if ATTR_RGB_COLOR in kwargs:
            rgb = kwargs[ATTR_RGB_COLOR]
            await self._device.set_rgb(brightness, rgb[0], rgb[1], rgb[2])
            return
        if ATTR_BRIGHTNESS in kwargs:
            await self._device.set_brightness(brightness)
            return
        await self._device.turn_on()

    @exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        _LOGGER.debug("Turning off light %s, address %s", kwargs, self._address)
        await self._device.turn_off()
