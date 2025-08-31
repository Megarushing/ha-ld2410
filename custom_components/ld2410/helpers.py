"""Helper utilities for the LD2410 integration."""

import asyncio

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later


async def _async_dismiss(hass: HomeAssistant, notification_id: str) -> None:
    """Dismiss a persistent notification."""
    persistent_notification.async_dismiss(hass, notification_id)


def async_ephemeral_notification(
    hass: HomeAssistant,
    message: str,
    *,
    title: str,
    notification_id: str,
    duration: float = 10,
) -> None:
    """Create a notification that dismisses itself after ``duration`` seconds."""
    persistent_notification.async_create(
        hass,
        message,
        title=title,
        notification_id=notification_id,
    )

    def _handle_dismiss(_: float) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is hass.loop:
            hass.async_create_task(_async_dismiss(hass, notification_id))
        else:
            hass.loop.call_soon_threadsafe(
                hass.async_create_task, _async_dismiss(hass, notification_id)
            )

    async_call_later(hass, duration, _handle_dismiss)
