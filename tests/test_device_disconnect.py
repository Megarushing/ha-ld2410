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
    device.cmd_enable_config = AsyncMock()
    device.cmd_enable_engineering_mode = AsyncMock()
    device.cmd_end_config = AsyncMock()

    device._disconnected(None)
    await asyncio.sleep(0)

    device._ensure_connected.assert_awaited_once()
    device.cmd_send_bluetooth_password.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconnect_after_timed_disconnect():
    """Ensure device reconnects after a timed disconnect."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device._restart_connection = AsyncMock()

    await device._execute_timed_disconnect()
    await asyncio.sleep(0)

    device._restart_connection.assert_awaited_once()
