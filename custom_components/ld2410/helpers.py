"""Helper utilities for the LD2410 integration."""

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

    async def _dismiss_cb(_: float) -> None:
        await _async_dismiss(hass, notification_id)

    async_call_later(hass, duration, _dismiss_cb)
