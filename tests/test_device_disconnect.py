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


@pytest.mark.asyncio
async def test_disconnected_cancels_operation() -> None:
    """Unexpected disconnect cancels any in-progress command."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )

    async def long_running(*_args, **_kwargs):
        await asyncio.sleep(100)

    with (
        patch(
            "custom_components.ld2410.api.devices.device.BLEAK_RETRY_EXCEPTIONS",
            (asyncio.CancelledError,),
        ),
        patch.object(device, "_send_command_locked", new=long_running),
        patch.object(device, "_restart_connection", AsyncMock()),
    ):
        task = asyncio.create_task(device._send_command("0000"))
        await asyncio.sleep(0)
        assert device._operation_lock.locked()
        device._disconnected(None)
        await asyncio.sleep(0)
        assert not device._operation_lock.locked()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_forced_disconnect_cancels_operation() -> None:
    """Forced disconnect during command cancels the operation."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )

    async def raise_timeout(*_args, **_kwargs):
        await asyncio.sleep(0)
        raise TimeoutError

    with (
        patch.object(device, "_execute_command_locked", new=raise_timeout),
        patch.object(device, "_execute_forced_disconnect", AsyncMock()),
        patch.object(device, "_ensure_connected", AsyncMock()),
    ):
        task = asyncio.create_task(device._send_command("0000"))
        await asyncio.sleep(0)
        assert device._operation_lock.locked()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not device._operation_lock.locked()


@pytest.mark.asyncio
async def test_ensure_connected_sends_password_when_not_connected() -> None:
    """_ensure_connected sends password on new connection."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    with (
        patch(
            "custom_components.ld2410.api.devices.device.Device._ensure_connected",
            AsyncMock(),
        ) as mock_connect,
        patch.object(device, "cmd_send_bluetooth_password", AsyncMock()) as mock_pass,
    ):
        await device._ensure_connected()

    mock_connect.assert_awaited_once()
    mock_pass.assert_awaited_once()


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
