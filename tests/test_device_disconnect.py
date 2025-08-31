import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSOR_TYPE,
)
from homeassistant.core import HomeAssistant

from custom_components.ld2410.api.devices.device import OperationError
from custom_components.ld2410.api.devices.ld2410 import LD2410
from custom_components.ld2410.const import DOMAIN

from . import LD2410b_SERVICE_INFO

try:
    from tests.common import MockConfigEntry
except ImportError:  # pragma: no cover
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import inject_bluetooth_service_info
except ImportError:  # pragma: no cover
    from .mocks import inject_bluetooth_service_info


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
    device.cmd_get_resolution = AsyncMock(return_value=0)
    device.cmd_get_light_config = AsyncMock()
    device._update_parsed_data = MagicMock()

    async def mock_connect():
        await device._on_connect()
        return True

    with (
        patch.object(
            device, "_ensure_connected", AsyncMock(side_effect=mock_connect)
        ) as mock_connect,
        patch.object(device, "cmd_send_bluetooth_password", AsyncMock()) as mock_pass,
    ):
        device._on_disconnect(None)
        await asyncio.sleep(1.1)

    mock_connect.assert_awaited_once()
    mock_pass.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_connect_can_send_commands_without_deadlock() -> None:
    """on_connect can safely send commands without deadlock."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    dummy_client = MagicMock()
    dummy_client.is_connected = True
    dummy_client.services = MagicMock()
    dummy_client.start_notify = AsyncMock()

    device._resolve_characteristics = MagicMock()
    device._start_notify = AsyncMock()
    device._reset_disconnect_timer = MagicMock()
    device._execute_command_locked = AsyncMock(return_value=b"")

    async def on_connect():
        await device._send_command("FF000101")

    device._on_connect = AsyncMock(side_effect=on_connect)

    with patch(
        "custom_components.ld2410.api.devices.device.establish_connection",
        AsyncMock(return_value=dummy_client),
    ):
        await asyncio.wait_for(device._send_command("FF000100"), 1)

    device._on_connect.assert_awaited_once()
    assert device._execute_command_locked.call_count == 2


@pytest.mark.asyncio
async def test_no_reconnect_when_disabled() -> None:
    """Device does not reconnect when _auto_reconnect is False."""

    class NoReconnectLD2410(LD2410):
        _auto_reconnect = False

    device = NoReconnectLD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    with patch.object(device.loop, "create_task", MagicMock()) as mock_task:
        device._on_disconnect(None)
    assert not mock_task.called


@pytest.mark.asyncio
async def test_reconnect_after_timed_disconnect():
    """Ensure device reconnects after a timed disconnect."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device._restart_connection = AsyncMock()
    await device._execute_timed_disconnect()
    device._on_disconnect(None)
    await asyncio.sleep(0)

    device._restart_connection.assert_awaited_once()


@pytest.mark.asyncio
async def test_restart_connection_waits_before_retry():
    """Reconnect waits a second before scheduling a retry."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device._on_connect = AsyncMock(side_effect=Exception("fail"))
    with patch(
        "custom_components.ld2410.api.devices.device.asyncio.sleep",
        new=AsyncMock(),
    ) as mock_sleep:

        def _close(coro):
            coro.close()

        with patch.object(device.loop, "create_task", side_effect=_close) as mock_task:
            await device._restart_connection()

    mock_sleep.assert_awaited_once_with(1)
    assert mock_task.call_count == 1


@pytest.mark.asyncio
async def test_restart_connection_cancels_previous_task() -> None:
    """Starting a new restart cancels any previous scheduled task."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )

    async def slow_connect() -> bool:
        await asyncio.sleep(0.1)
        return True

    device._ensure_connected = AsyncMock(side_effect=slow_connect)
    device._on_connect = AsyncMock()

    first = device.loop.create_task(device._restart_connection())
    device._restart_connection_tasks.append(first)
    await asyncio.sleep(0)
    second = device.loop.create_task(device._restart_connection())
    device._restart_connection_tasks.append(second)
    await asyncio.sleep(0.2)

    assert first.cancelled()
    assert second.done()
    assert device._restart_connection_tasks == []


@pytest.mark.asyncio
async def test_restart_connection_cancelled_does_not_reschedule() -> None:
    """Cancelling restart does not schedule another reconnect."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )

    async def slow_connect() -> bool:
        await asyncio.sleep(3600)
        return True

    device._ensure_connected = AsyncMock(side_effect=slow_connect)
    device._on_connect = AsyncMock()

    orig_create_task = device.loop.create_task
    with patch.object(
        device.loop, "create_task", wraps=orig_create_task
    ) as mock_create_task:
        task = device.loop.create_task(device._restart_connection())
        device._restart_connection_tasks.append(task)
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)
    assert device._restart_connection_tasks == []
    assert mock_create_task.call_count == 1


@pytest.mark.asyncio
async def test_restart_connection_skips_on_connect_if_already_connected() -> None:
    """on_connect is not called when already connected."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device._client = AsyncMock(is_connected=True)
    with (
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._ensure_connected",
            AsyncMock(return_value=False),
        ) as mock_connect,
        patch.object(device, "_on_connect", AsyncMock()) as mock_on_connect,
    ):
        await device._restart_connection()

    mock_connect.assert_awaited_once()
    mock_on_connect.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_clears_command_queue() -> None:
    """Disconnect clears queued commands and releases the lock."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device._ensure_connected = AsyncMock()
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


@pytest.mark.asyncio
async def test_reload_does_not_reconnect_old_device(hass: HomeAssistant) -> None:
    """Reloading the entry does not trigger reconnect of the old device."""

    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "abc123",
            CONF_SENSOR_TYPE: "ld2410",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_hass(hass)

    async def mock_ensure_connected(self):
        await self._on_connect()
        return True

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._ensure_connected",
            mock_ensure_connected,
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ) as mock_pass,
        patch("custom_components.ld2410.api.LD2410.cmd_enable_config", AsyncMock()),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_engineering_mode",
            AsyncMock(),
        ),
        patch("custom_components.ld2410.api.LD2410.cmd_end_config", AsyncMock()),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_read_params",
            AsyncMock(
                return_value={
                    "move_gate_sensitivity": [],
                    "still_gate_sensitivity": [],
                    "absence_delay": 0,
                }
            ),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_get_resolution",
            AsyncMock(return_value=0),
        ),
        patch("custom_components.ld2410.api.LD2410.cmd_get_light_config", AsyncMock()),
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._update_parsed_data",
            autospec=True,
        ),
        patch.object(LD2410, "_restart_connection", AsyncMock()) as mock_restart,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert mock_pass.call_count == 2
    mock_restart.assert_not_called()


@pytest.mark.asyncio
async def test_unload_cancels_restart_task(hass: HomeAssistant) -> None:
    """Unloading the entry cancels any scheduled reconnect task."""

    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "abc123",
            CONF_SENSOR_TYPE: "ld2410",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_hass(hass)

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._ensure_connected",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
        patch("custom_components.ld2410.api.LD2410.cmd_enable_config", AsyncMock()),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_enable_engineering_mode",
            AsyncMock(),
        ),
        patch("custom_components.ld2410.api.LD2410.cmd_end_config", AsyncMock()),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_read_params",
            AsyncMock(
                return_value={
                    "move_gate_sensitivity": [],
                    "still_gate_sensitivity": [],
                    "absence_delay": 0,
                }
            ),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_get_resolution",
            AsyncMock(return_value=0),
        ),
        patch("custom_components.ld2410.api.LD2410.cmd_get_light_config", AsyncMock()),
        patch(
            "custom_components.ld2410.api.devices.device.BaseDevice._update_parsed_data",
            autospec=True,
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    device = entry.runtime_data.device

    restart_cancelled = asyncio.Event()

    async def fake_restart() -> None:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            restart_cancelled.set()
            raise

    device._restart_connection = fake_restart
    task = device.loop.create_task(device._restart_connection())
    device._restart_connection_tasks.append(task)
    await asyncio.sleep(0)

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert restart_cancelled.is_set()
    assert device._restart_connection_tasks == []


@pytest.mark.asyncio
async def test_on_disconnect_clears_command_queue() -> None:
    """Unexpected disconnect clears queued commands and releases the lock."""
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password="HiLink",
    )
    device._ensure_connected = AsyncMock()
    await device._operation_lock.acquire()
    task1 = asyncio.create_task(device._send_command("FF000100"))
    task2 = asyncio.create_task(device._send_command("FF000100"))
    await asyncio.sleep(0)
    device._should_reconnect = False
    device._on_disconnect(None)
    await asyncio.sleep(0)
    for task in (task1, task2):
        with pytest.raises(OperationError):
            await task
    assert not device._operation_lock.locked()
