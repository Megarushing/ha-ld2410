import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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
    device.cmd_read_params = AsyncMock(
        return_value={
            "move_gate_sensitivity": [],
            "still_gate_sensitivity": [],
            "nobody_duration": 0,
        }
    )
    device._update_parsed_data = MagicMock()

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


@pytest.mark.asyncio
async def test_restart_connection_waits_before_retry():
    """Reconnect waits a second before scheduling a retry."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device.connect_and_subscribe = AsyncMock(side_effect=Exception("fail"))
    with patch(
        "custom_components.ld2410.api.devices.ld2410.asyncio.sleep",
        new=AsyncMock(),
    ) as mock_sleep:

        def _close(coro):
            coro.close()

        with patch.object(device.loop, "create_task", side_effect=_close) as mock_task:
            await device._restart_connection()

    mock_sleep.assert_awaited_once_with(1)
    assert mock_task.call_count == 1
