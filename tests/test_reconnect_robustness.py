"""Regression tests for the 2026-11-10 stuck-reconnect outage."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from custom_components.ld2410.api.devices import device as device_module
from custom_components.ld2410.api.devices.device import (
    RECONNECT_BACKOFF_MAX,
    RECONNECT_GRACE,
)
from custom_components.ld2410.api.devices.ld2410 import LD2410


def _device() -> LD2410:
    return LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )


async def _failed_reconnect_delays(device: LD2410, attempts: int) -> list[float]:
    """Run ``attempts`` failing reconnects; return each retry delay."""
    device._ensure_connected = AsyncMock(side_effect=BleakError("no slot"))
    sleep = AsyncMock()
    with (
        patch.object(device_module.asyncio, "sleep", sleep),
        patch.object(device, "schedule_reconnect"),
    ):
        for _ in range(attempts):
            await device._restart_connection()
    return [call.args[0] for call in sleep.await_args_list]


async def test_reconnect_backs_off_up_to_the_cap() -> None:
    """Each failed reconnect doubles the wait instead of retrying every 1 s."""
    device = _device()
    delays = await _failed_reconnect_delays(device, 7)
    assert delays == [1, 2, 4, 8, 16, RECONNECT_BACKOFF_MAX, RECONNECT_BACKOFF_MAX]


async def test_backoff_resets_after_successful_setup() -> None:
    """A fully set-up connection starts the next outage at the short delay."""
    device = _device()
    await _failed_reconnect_delays(device, 3)
    del device._ensure_connected  # back to the real method
    client = MagicMock(is_connected=True)
    device._on_connect = AsyncMock()
    with (
        patch.object(
            device_module, "establish_connection", AsyncMock(return_value=client)
        ),
        patch.object(device, "_resolve_characteristics"),
        patch.object(device, "_start_notify", AsyncMock()),
    ):
        assert await device._ensure_connected() is True
    device._cancel_disconnect_timer()
    device._client = None
    assert await _failed_reconnect_delays(device, 1) == [1]


async def test_failed_disconnect_is_retried_once() -> None:
    """A disconnect that times out is sent again so the proxy frees the slot."""
    device = _device()
    client = MagicMock()
    client.disconnect = AsyncMock(side_effect=[BleakError("timeout"), None])
    device._client = client
    with patch.object(device, "schedule_reconnect") as reconnect:
        async with device._connect_lock:
            await device._execute_disconnect_with_lock()
    assert client.disconnect.await_count == 2
    reconnect.assert_called_once()


async def test_disconnect_not_repeated_after_success() -> None:
    """A successful disconnect is sent only once."""
    device = _device()
    client = MagicMock()
    client.disconnect = AsyncMock()
    device._client = client
    with patch.object(device, "schedule_reconnect"):
        async with device._connect_lock:
            await device._execute_disconnect_with_lock()
    assert client.disconnect.await_count == 1


async def test_disconnect_gives_up_after_two_failures() -> None:
    """Two failed disconnects still end in a scheduled reconnect."""
    device = _device()
    client = MagicMock()
    client.disconnect = AsyncMock(side_effect=BleakError("timeout"))
    device._client = client
    with patch.object(device, "schedule_reconnect") as reconnect:
        async with device._connect_lock:
            await device._execute_disconnect_with_lock()
    assert client.disconnect.await_count == 2
    reconnect.assert_called_once()


async def test_initial_connect_starts_grace_period() -> None:
    """Entities go unavailable if the very first setup never completes."""
    device = _device()
    device._ensure_connected = AsyncMock(side_effect=asyncio.CancelledError)
    with patch.object(device_module.time, "monotonic", return_value=1000.0):
        device.start_connecting()
    assert device._grace_timer is not None
    with patch.object(
        device_module.time, "monotonic", return_value=1000.0 + RECONNECT_GRACE
    ):
        assert device.reconnect_overdue
    device.clear_reconnect_grace()
    device._initial_connect_task.cancel()


async def test_idle_timer_does_not_disconnect_during_setup() -> None:
    """A slow setup is not mistaken for a dead uplink stream."""
    device = _device()
    device._client = MagicMock(is_connected=True)
    device._setting_up = True
    with patch.object(device, "_execute_timed_disconnect", AsyncMock()) as timed:
        device._disconnect_from_timer()
        await asyncio.sleep(0)
    timed.assert_not_called()
    assert device._disconnect_timer is not None
    device._cancel_disconnect_timer()


async def test_idle_timer_disconnects_silent_stream_after_setup() -> None:
    """The silence watchdog still works once setup is done."""
    device = _device()
    device._client = MagicMock(is_connected=True)
    with patch.object(device, "_execute_timed_disconnect", AsyncMock()) as timed:
        device._disconnect_from_timer()
        await asyncio.sleep(0)
    timed.assert_awaited_once()


async def test_setup_flag_cleared_when_on_connect_fails() -> None:
    """A failed setup does not leave the watchdog disabled."""
    device = _device()
    device._on_connect = AsyncMock(side_effect=BleakError("no reply"))
    with (
        patch.object(
            device_module,
            "establish_connection",
            AsyncMock(return_value=MagicMock(is_connected=True)),
        ),
        patch.object(device, "_resolve_characteristics"),
        patch.object(device, "_start_notify", AsyncMock()),
        pytest.raises(BleakError),
    ):
        await device._ensure_connected()
    assert device._setting_up is False
    device._cancel_disconnect_timer()


async def test_setup_flag_cleared_when_connect_fails() -> None:
    """A failed BLE connect does not leave the watchdog disabled."""
    device = _device()
    with (
        patch.object(
            device_module,
            "establish_connection",
            AsyncMock(side_effect=BleakError("timeout")),
        ),
        pytest.raises(BleakError),
    ):
        await device._ensure_connected()
    assert device._setting_up is False


async def test_waiting_caller_keeps_setup_flag_of_connecting_task() -> None:
    """A caller that waited on the lock must not clear the flag mid-setup."""
    device = _device()
    release = asyncio.Event()
    seen: list[bool] = []

    async def slow_on_connect() -> None:
        await asyncio.sleep(0)  # let the waiting caller finish first
        await asyncio.sleep(0)
        seen.append(device._setting_up)
        release.set()

    device._on_connect = slow_on_connect
    with (
        patch.object(
            device_module,
            "establish_connection",
            AsyncMock(return_value=MagicMock(is_connected=True)),
        ),
        patch.object(device, "_resolve_characteristics"),
        patch.object(device, "_start_notify", AsyncMock()),
    ):
        first = asyncio.create_task(device._ensure_connected())
        await asyncio.sleep(0)
        second = asyncio.create_task(device._ensure_connected())
        assert await second is False
        await release.wait()
        assert await first is True
    assert seen == [True]
    assert device._setting_up is False
    device._cancel_disconnect_timer()
