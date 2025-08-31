from unittest.mock import patch

from custom_components.ld2410.helpers import async_ephemeral_notification


async def test_async_ephemeral_notification_dismisses(hass):
    """Notification is dismissed without thread-safety error."""
    with (
        patch(
            "custom_components.ld2410.helpers.persistent_notification.async_create"
        ) as mock_create,
        patch(
            "custom_components.ld2410.helpers.persistent_notification.async_dismiss"
        ) as mock_dismiss,
    ):
        async_ephemeral_notification(
            hass, "message", title="title", notification_id="notif", duration=0
        )
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    mock_create.assert_called_once()
    mock_dismiss.assert_called_once_with(hass, "notif")
