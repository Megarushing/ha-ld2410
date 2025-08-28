import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from custom_components.ld2410.api.devices.device import OperationError
from custom_components.ld2410.api.devices.ld2410 import LD2410


@pytest.mark.asyncio
async def test_reconnect_after_unexpected_disconnect():
    """Ensure device reconnects and reauthorizes on unexpected disconnect."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device.cmd_enable_config = AsyncMock()
    device.cmd_enable_engineering_mode = AsyncMock()
    device.cmd_end_config = AsyncMock()
    device.cmd_read_params = AsyncMock(
        return_value={
            "move_gate_sensitivity": [],
            "still_gate_sensitivity": [],
            "absence_delay": 0,
        }
    )
    device._update_parsed_data = MagicMock()

    with (
        patch(
            "custom_components.ld2410.api.devices.device.Device._ensure_connected",
            AsyncMock(),
        ) as mock_connect,
        patch.object(device, "cmd_send_bluetooth_password", AsyncMock()) as mock_pass,
    ):
        device._disconnected(None)
        await asyncio.sleep(0)

    mock_connect.assert_awaited_once()
    mock_pass.assert_awaited_once()


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
    device.connect_and_update = AsyncMock(side_effect=Exception("fail"))
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


@pytest.mark.asyncio
async def test_ensure_connected_skips_password_when_already_connected() -> None:
    """_ensure_connected does not send password if already connected."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device._client = AsyncMock(is_connected=True)
    with (
        patch(
            "custom_components.ld2410.api.devices.device.Device._ensure_connected",
            AsyncMock(),
        ) as mock_connect,
        patch.object(device, "cmd_send_bluetooth_password", AsyncMock()) as mock_pass,
    ):
        await device._ensure_connected()

    mock_connect.assert_awaited_once()
    mock_pass.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_clears_command_queue() -> None:
    """Disconnect clears queued commands and releases the lock."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    await device._operation_lock.acquire()
    task1 = asyncio.create_task(device._send_command("FF000100"))
    task2 = asyncio.create_task(device._send_command("FF000100"))
    await asyncio.sleep(0)
    device._client = AsyncMock()
    device._client.disconnect = AsyncMock()
    async with device._connect_lock:
        await device._execute_disconnect_with_lock()
    await asyncio.sleep(0)
    for task in (task1, task2):
        with pytest.raises(OperationError):
            await task
    assert not device._operation_lock.locked()
