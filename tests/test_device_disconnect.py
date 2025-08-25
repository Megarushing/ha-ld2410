import asyncio
from unittest.mock import AsyncMock

import pytest
from bleak.backends.device import BLEDevice

from custom_components.ld2410.api.devices.ld2410 import LD2410


@pytest.mark.asyncio
async def test_reconnect_after_unexpected_disconnect():
    """Ensure device reconnects and reauthorizes on unexpected disconnect."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device._ensure_connected = AsyncMock()
    device.cmd_send_bluetooth_password = AsyncMock()

    device._disconnected(None)
    await asyncio.sleep(0)

    device._ensure_connected.assert_awaited_once()
    device.cmd_send_bluetooth_password.assert_awaited_once()
