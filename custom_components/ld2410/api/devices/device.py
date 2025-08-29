"""Library to handle device connection."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak.exc import BleakDBusError
from bleak_retry_connector import (
    BLEAK_RETRY_EXCEPTIONS,
    BleakClientWithServiceCache,
    BleakNotFoundError,
    ble_device_has_changed,
    establish_connection,
)

from ..const import (
    CHARACTERISTIC_NOTIFY,
    CHARACTERISTIC_WRITE,
    DEFAULT_RETRY_COUNT,
    DEFAULT_SCAN_TIMEOUT,
)
from ..discovery import GetDevices
from ..models import Advertisement

_LOGGER = logging.getLogger(__name__)


DBUS_ERROR_BACKOFF_TIME = 0.25

# How long to hold the connection
# to wait for additional commands for
# disconnecting the device.
DISCONNECT_DELAY = 8.5


# If the scanner is in passive mode, we
# need to poll the device to get the
# battery and a few rarely updating
# values.
PASSIVE_POLL_INTERVAL = 60 * 60 * 24


class CharacteristicMissingError(Exception):
    """Raised when a characteristic is missing."""


class OperationError(Exception):
    """Raised when an operation fails."""


def _merge_data(old_data: dict[str, Any], new_data: dict[str, Any]) -> dict[str, Any]:
    """Merge data but only add None keys if they are missing."""
    merged = old_data.copy()
    for key, value in new_data.items():
        if isinstance(value, dict) and isinstance(old_data.get(key), dict):
            merged[key] = _merge_data(old_data[key], value)
        elif value is not None or key not in old_data:
            merged[key] = value
    return merged


def _handle_timeout(fut: asyncio.Future[None]) -> None:
    """Handle a timeout."""
    if not fut.done():
        fut.set_exception(asyncio.TimeoutError)


class BaseDevice:
    """Base representation of a device."""

    _auto_reconnect: bool = False

    def __init__(
        self,
        device: BLEDevice,
        interface: int = 0,
        **kwargs: Any,
    ) -> None:
        """Base class constructor."""
        self._interface = f"hci{interface}"
        self._device = device
        self._sb_adv_data: Advertisement | None = None
        self._override_adv_data: dict[str, Any] | None = None
        self._scan_timeout: int = kwargs.pop("scan_timeout", DEFAULT_SCAN_TIMEOUT)
        self._retry_count: int = kwargs.pop("retry_count", DEFAULT_RETRY_COUNT)
        self._connect_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        self._auto_reconnect = getattr(self, "_auto_reconnect", False)
        self._client: BleakClientWithServiceCache | None = None
        self._read_char: BleakGATTCharacteristic | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._expected_disconnect = False
        self.loop = asyncio.get_event_loop()
        self._callbacks: list[Callable[[], None]] = []
        self._notify_future: asyncio.Future[bytearray] | None = None
        self._last_full_update: float = -PASSIVE_POLL_INTERVAL
        self._timed_disconnect_task: asyncio.Task[None] | None = None
        self._rssi: int = getattr(device, "rssi", -127) or -127

    def advertisement_changed(self, advertisement: Advertisement) -> bool:
        """Check if the advertisement has changed."""
        return bool(
            not self._sb_adv_data
            or ble_device_has_changed(self._sb_adv_data.device, advertisement.device)
            or advertisement.data != self._sb_adv_data.data
        )

    def _modify_command(self, raw_command: str) -> bytes:
        """Return command bytes, optionally modified by subclasses."""
        return bytearray.fromhex(raw_command)

    def _parse_response(self, raw_command: str, data: bytes) -> bytes:
        """Return raw response data.

        Subclasses may override to parse protocol-specific responses.
        """
        return data

    async def _send_command_locked_with_retry(
        self,
        raw_command: str,
        command: bytes,
        retry: int,
        max_attempts: int,
        wait_for_response: bool,
    ) -> bytes | None:
        for attempt in range(max_attempts):
            try:
                return await self._send_command_locked(
                    raw_command, command, wait_for_response
                )
            except BleakNotFoundError:
                _LOGGER.error(
                    "%s: device not found, no longer in range, or poor RSSI: %s",
                    self.name,
                    self.rssi,
                    exc_info=True,
                )
                raise
            except CharacteristicMissingError as ex:
                if attempt == retry:
                    _LOGGER.error(
                        "%s: characteristic missing: %s; Stopping trying; RSSI: %s",
                        self.name,
                        ex,
                        self.rssi,
                        exc_info=True,
                    )
                    raise

                _LOGGER.debug(
                    "%s: characteristic missing: %s; RSSI: %s",
                    self.name,
                    ex,
                    self.rssi,
                    exc_info=True,
                )
            except BLEAK_RETRY_EXCEPTIONS:
                if attempt == retry:
                    _LOGGER.error(
                        "%s: communication failed; Stopping trying; RSSI: %s",
                        self.name,
                        self.rssi,
                        exc_info=True,
                    )
                    raise

                _LOGGER.debug(
                    "%s: communication failed with:", self.name, exc_info=True
                )

        raise RuntimeError("Unreachable")

    async def _send_command(
        self,
        raw_command: str,
        retry: int | None = None,
        *,
        wait_for_response: bool = True,
    ) -> bytes | None:
        """Send command to device and optionally read response."""
        if retry is None:
            retry = self._retry_count
        command = self._modify_command(raw_command)
        max_attempts = retry + 1
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        async with self._operation_lock:
            return await self._send_command_locked_with_retry(
                raw_command, command, retry, max_attempts, wait_for_response
            )

    @property
    def name(self) -> str:
        """Return device name."""
        return f"{self._device.name} ({self._device.address})"

    @property
    def data(self) -> dict[str, Any]:
        """Return device data."""
        if self._sb_adv_data:
            return self._sb_adv_data.data
        return {}

    @property
    def parsed_data(self) -> dict[str, Any]:
        """Return parsed device data."""
        return self.data.get("data") or {}

    @property
    def rssi(self) -> int:
        """Return RSSI of device."""
        return self._rssi

    async def read_rssi(self) -> int | None:
        """Update and return the RSSI using the active connection."""
        if self._client and self._client.is_connected:
            with contextlib.suppress(Exception):
                rssi = await self._client.get_rssi()  # type: ignore[attr-defined]
                if isinstance(rssi, int):
                    self._rssi = rssi
                    if self._sb_adv_data:
                        self._sb_adv_data = replace(self._sb_adv_data, rssi=rssi)
                    else:
                        self._sb_adv_data = Advertisement(
                            address=self._device.address,
                            data={},
                            device=self._device,
                            rssi=rssi,
                        )
                    return rssi
        if self._sb_adv_data:
            self._rssi = self._sb_adv_data.rssi
            return self._rssi
        return None

    @property
    def is_connected(self) -> bool:
        """Return if the BLE client is connected."""
        return bool(self._client and self._client.is_connected)

    async def _ensure_connected(self) -> bool:
        """Ensure connection to device is established.

        Returns True if a new connection was made.
        """
        if self._connect_lock.locked():
            _LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        if self._client and self._client.is_connected:
            _LOGGER.debug(
                "%s: Already connected before obtaining lock, resetting timer; RSSI: %s",
                self.name,
                self.rssi,
            )
            self._reset_disconnect_timer()
            return False
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                _LOGGER.debug(
                    "%s: Already connected after obtaining lock, resetting timer; RSSI: %s",
                    self.name,
                    self.rssi,
                )
                self._reset_disconnect_timer()
                return False
            _LOGGER.debug("%s: Connecting; RSSI: %s", self.name, self.rssi)
            client: BleakClientWithServiceCache = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self.name,
                self._disconnected,
                use_services_cache=True,
                ble_device_callback=lambda: self._device,
            )
            _LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            self._client = client

            try:
                self._resolve_characteristics(client.services)
            except CharacteristicMissingError as ex:
                _LOGGER.debug(
                    "%s: characteristic missing, clearing cache: %s; RSSI: %s",
                    self.name,
                    ex,
                    self.rssi,
                    exc_info=True,
                )
                await client.clear_cache()
                self._cancel_disconnect_timer()
                await self._execute_disconnect_with_lock()
                raise

            _LOGGER.debug(
                "%s: Starting notify and disconnect timer; RSSI: %s",
                self.name,
                self.rssi,
            )
            self._reset_disconnect_timer()
            await self._start_notify()
            return True

    def _resolve_characteristics(self, services: BleakGATTServiceCollection) -> None:
        """Resolve characteristics."""
        self._read_char = services.get_characteristic(CHARACTERISTIC_NOTIFY)
        if not self._read_char:
            raise CharacteristicMissingError(CHARACTERISTIC_NOTIFY)
        self._write_char = services.get_characteristic(CHARACTERISTIC_WRITE)
        if not self._write_char:
            raise CharacteristicMissingError(CHARACTERISTIC_WRITE)

    def _reset_disconnect_timer(self):
        """Reset disconnect timer."""
        self._cancel_disconnect_timer()
        self._expected_disconnect = False
        self._disconnect_timer = self.loop.call_later(
            DISCONNECT_DELAY, self._disconnect_from_timer
        )

    def _clear_locked_commands(self):
        if self._operation_lock.locked() or getattr(
            self._operation_lock, "_waiters", []
        ):
            _LOGGER.debug("%s: Clearing queued commands before disconnect", self.name)
            waiters = list(getattr(self._operation_lock, "_waiters", []))
            for waiter in waiters:
                if not waiter.done():
                    waiter.set_exception(OperationError("Device disconnecting"))
            self._operation_lock = asyncio.Lock()

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if self._expected_disconnect:
            _LOGGER.debug(
                "%s: Disconnected from device; RSSI: %s", self.name, self.rssi
            )
            return
        _LOGGER.warning(
            "%s: Device unexpectedly disconnected; RSSI: %s",
            self.name,
            self.rssi,
        )
        self._cancel_disconnect_timer()
        if self._auto_reconnect:
            self.loop.create_task(self._restart_connection())

    def _disconnect_from_timer(self):
        """Disconnect from device."""
        if self._operation_lock.locked() and self._client.is_connected:
            _LOGGER.debug(
                "%s: Operation in progress, resetting disconnect timer; RSSI: %s",
                self.name,
                self.rssi,
            )
            self._reset_disconnect_timer()
            return
        self._cancel_disconnect_timer()
        self._timed_disconnect_task = asyncio.create_task(
            self._execute_timed_disconnect()
        )

    def _cancel_disconnect_timer(self):
        """Cancel disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None

    async def async_disconnect(self) -> None:
        """Disconnect the device and stop active notifications."""
        self._cancel_disconnect_timer()
        client = self._client
        if client and self._read_char:
            try:
                await client.stop_notify(self._read_char)
            except BLEAK_RETRY_EXCEPTIONS as ex:
                _LOGGER.debug("%s: Error stopping notify: %s", self.name, ex)
        await self._execute_disconnect()

    async def _execute_forced_disconnect(self) -> None:
        """Execute forced disconnection."""
        self._cancel_disconnect_timer()
        _LOGGER.debug(
            "%s: Executing forced disconnect",
            self.name,
        )
        await self._execute_disconnect()

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection."""
        _LOGGER.debug(
            "%s: Executing timed disconnect after timeout of %s",
            self.name,
            DISCONNECT_DELAY,
        )
        await self._execute_disconnect()
        if self._auto_reconnect:
            self.loop.create_task(self._restart_connection())

    async def on_connect(self) -> None:
        """Run after a new connection is made."""
        return

    async def _restart_connection(self) -> None:
        """Reconnect after an unexpected disconnect."""
        try:
            _LOGGER.debug("%s: Reconnecting...", self.name)
            connected = await self._ensure_connected()
            if connected:
                await self.on_connect()
        except Exception as ex:  # pragma: no cover - best effort
            _LOGGER.debug("%s: Reconnect failed: %s", self.name, ex)
            await asyncio.sleep(1)
            self.loop.create_task(self._restart_connection())

    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        _LOGGER.debug("%s: Executing disconnect", self.name)
        async with self._connect_lock:
            await self._execute_disconnect_with_lock()

    async def _execute_disconnect_with_lock(self) -> None:
        """Execute disconnection while holding the lock."""
        assert self._connect_lock.locked(), "Lock not held"
        _LOGGER.debug("%s: Executing disconnect with lock", self.name)
        if self._disconnect_timer:  # If the timer was reset, don't disconnect
            _LOGGER.debug("%s: Skipping disconnect as timer reset", self.name)
            return
        self._clear_locked_commands()
        client = self._client
        self._expected_disconnect = True
        self._client = None
        self._read_char = None
        self._write_char = None
        if not client:
            _LOGGER.debug("%s: Already disconnected", self.name)
            return
        _LOGGER.debug("%s: Disconnecting", self.name)
        try:
            await client.disconnect()
        except BLEAK_RETRY_EXCEPTIONS as ex:
            _LOGGER.warning(
                "%s: Error disconnecting: %s; RSSI: %s",
                self.name,
                ex,
                self.rssi,
            )
        else:
            _LOGGER.debug("%s: Disconnect completed successfully", self.name)

    async def _send_command_locked(
        self, raw_command: str, command: bytes, wait_for_response: bool
    ) -> bytes | None:
        """Send command to device and optionally read response."""
        await self._ensure_connected()
        try:
            return await self._execute_command_locked(
                raw_command, command, wait_for_response
            )
        except BleakDBusError as ex:
            # Disconnect so we can reset state and try again
            await asyncio.sleep(DBUS_ERROR_BACKOFF_TIME)
            _LOGGER.debug(
                "%s: RSSI: %s; Backing off %ss; Disconnecting due to error: %s",
                self.name,
                self.rssi,
                DBUS_ERROR_BACKOFF_TIME,
                ex,
            )
            await self._execute_forced_disconnect()
            raise
        except BLEAK_RETRY_EXCEPTIONS as ex:
            # Disconnect so we can reset state and try again
            _LOGGER.debug(
                "%s: RSSI: %s; Disconnecting due to error: %s", self.name, self.rssi, ex
            )
            await self._execute_forced_disconnect()
            raise

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""
        self._reset_disconnect_timer()
        if not self._handle_notification(data):
            _LOGGER.debug(
                "%s: Received unknown notification: %s", self.name, data.hex()
            )

    def _handle_notification(self, data: bytearray) -> bool:
        """Handle notification, return True if handled."""
        if self._notify_future and not self._notify_future.done():
            self._notify_future.set_result(data)
            return True
        return False

    async def _start_notify(self) -> None:
        """Start notification."""
        _LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
        await self._client.start_notify(self._read_char, self._notification_handler)

    async def _execute_command_locked(
        self, raw_command: str, command: bytes, wait_for_response: bool
    ) -> bytes | None:
        """Execute command and optionally read response."""
        assert self._client is not None
        assert self._read_char is not None
        assert self._write_char is not None
        client = self._client

        _LOGGER.debug("%s: Sending command: %s", self.name, raw_command)
        if wait_for_response:
            self._notify_future = self.loop.create_future()
        await client.write_gatt_char(self._write_char, command, False)
        if not wait_for_response:
            return None
        timeout = 5
        timeout_handle = self.loop.call_at(
            self.loop.time() + timeout, _handle_timeout, self._notify_future
        )
        timeout_expired = False
        try:
            notify_msg_raw = await self._notify_future
        except TimeoutError:
            timeout_expired = True
            raise
        finally:
            if not timeout_expired:
                timeout_handle.cancel()
            self._notify_future = None

        notify_msg = self._parse_response(raw_command, notify_msg_raw)
        _LOGGER.debug("%s: Command reponse: %s", self.name, notify_msg.hex())
        return notify_msg

    def get_address(self) -> str:
        """Return address of device."""
        return self._device.address

    def _override_state(self, state: dict[str, Any]) -> None:
        """Override device state."""
        if self._override_adv_data is None:
            self._override_adv_data = {}
        self._override_adv_data.update(state)
        self._update_parsed_data(state)

    def _get_adv_value(self, key: str, channel: int | None = None) -> Any:
        """Return value from advertisement data."""
        if self._override_adv_data and key in self._override_adv_data:
            _LOGGER.debug(
                "%s: Using override value for %s: %s",
                self.name,
                key,
                self._override_adv_data[key],
            )
            return self._override_adv_data[key]
        if not self._sb_adv_data:
            return None
        if channel is not None:
            return self._sb_adv_data.data["data"].get(channel, {}).get(key)
        return self._sb_adv_data.data["data"].get(key)

    def get_battery_percent(self) -> Any:
        """Return device battery level in percent."""
        return self._get_adv_value("battery")

    def update_from_advertisement(self, advertisement: Advertisement) -> None:
        """Update device data from advertisement."""
        # Only accept advertisements if the data is not missing
        # if we already have an advertisement with data
        self._device = advertisement.device

    async def get_device_data(
        self, retry: int | None = None, interface: int | None = None
    ) -> Advertisement | None:
        """Find devices and their advertisement data."""
        if retry is None:
            retry = self._retry_count

        if interface:
            _interface: int = interface
        else:
            _interface = int(self._interface.replace("hci", ""))

        _data = await GetDevices(interface=_interface).discover(
            retry=retry, scan_timeout=self._scan_timeout
        )

        if self._device.address in _data:
            self._sb_adv_data = _data[self._device.address]

        return self._sb_adv_data

    def _fire_callbacks(self) -> None:
        """Fire callbacks."""
        # _LOGGER.debug("%s: Fire callbacks", self.name)
        for callback in self._callbacks:
            callback()

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to device notifications."""
        self._callbacks.append(callback)

        def _unsub() -> None:
            """Unsubscribe from device notifications."""
            self._callbacks.remove(callback)

        return _unsub

    async def update(self, interface: int | None = None) -> None:
        """Update position, battery percent and light level of device."""
        if info := await self.get_basic_info():
            self._last_full_update = time.monotonic()
            self._update_parsed_data(info)
            self._fire_callbacks()

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Return cached device data."""
        return self.parsed_data or None

    def _check_command_result(
        self, result: bytes | None, index: int, values: set[int]
    ) -> bool:
        """Check command result."""
        if not result or len(result) - 1 < index:
            result_hex = result.hex() if result else "None"
            raise OperationError(
                f"{self.name}: Sending command failed (result={result_hex} index={index} expected={values} rssi={self.rssi})"
            )
        return result[index] in values

    def _update_parsed_data(self, new_data: dict[str, Any]) -> bool:
        """
        Update data.

        Returns true if data has changed and False if not.
        """
        if not self._sb_adv_data:
            # Initialize advertisement data if we have not yet received any
            self._sb_adv_data = Advertisement(
                address=self._device.address,
                data={"data": new_data},
                device=self._device,
                rssi=self.rssi,
            )
            # _LOGGER.debug("%s: Updated data: %s", self.name, new_data)
            return True
        old_data = self._sb_adv_data.data.get("data") or {}
        merged_data = _merge_data(old_data, new_data)
        if merged_data == old_data:
            return False
        self._set_parsed_data(self._sb_adv_data, merged_data)
        # _LOGGER.debug("%s: Updated data: %s", self.name, merged_data)
        return True

    def _set_parsed_data(
        self, advertisement: Advertisement, data: dict[str, Any]
    ) -> None:
        """Set data."""
        self._sb_adv_data = replace(
            advertisement, data=self._sb_adv_data.data | {"data": data}
        )

    def _set_advertisement_data(self, advertisement: Advertisement) -> None:
        """Set advertisement data."""
        new_data = advertisement.data.get("data") or {}
        if advertisement.active:
            # If we are getting active data, we can assume we are
            # getting active scans and we do not need to poll
            self._last_full_update = time.monotonic()
        if not self._sb_adv_data:
            self._sb_adv_data = advertisement
        elif new_data:
            self._update_parsed_data(new_data)
        self._rssi = advertisement.rssi
        self._override_adv_data = None

    def poll_needed(self, seconds_since_last_poll: float | None) -> bool:
        """Return if device needs polling."""
        if (
            seconds_since_last_poll is not None
            and seconds_since_last_poll < PASSIVE_POLL_INTERVAL
        ):
            return False
        time_since_last_full_update = time.monotonic() - self._last_full_update
        return not time_since_last_full_update < PASSIVE_POLL_INTERVAL

    def _check_function_support(self, cmd: str | None = None) -> None:
        """Check if the command is supported by the device model."""
        if not cmd:
            raise OperationError(
                f"Current device {self._device.address} does not support this functionality"
            )


class Device(BaseDevice):
    """Representation of a device."""

    def update_from_advertisement(self, advertisement: Advertisement) -> None:
        """Update device data from advertisement."""
        super().update_from_advertisement(advertisement)
        self._set_advertisement_data(advertisement)
