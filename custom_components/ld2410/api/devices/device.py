"""Library to handle device connection."""

from __future__ import annotations

import asyncio
import binascii
import logging
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any, TypeVar, cast

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
    TX_HEADER,
    TX_FOOTER,
    RX_HEADER,
    RX_FOOTER,
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


WrapFuncType = TypeVar("WrapFuncType", bound=Callable[..., Any])


def update_after_operation(func: WrapFuncType) -> WrapFuncType:
    """Define a wrapper to update after an operation."""

    async def _async_update_after_operation_wrap(
        self: BaseDevice, *args: Any, **kwargs: Any
    ) -> None:
        ret = await func(self, *args, **kwargs)
        await self.update()
        return ret

    return cast(WrapFuncType, _async_update_after_operation_wrap)


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


def _password_to_words(password: str) -> tuple[str, ...]:
    """Encode an ASCII password into 16-bit word hex strings."""
    data = password.encode("ascii")
    if len(data) % 2:
        data += b"\x00"
    return tuple(data[i : i + 2].hex() for i in range(0, len(data), 2))


def _wrap_command(key: str) -> bytes:
    """Wrap a command with header, length and footer."""
    command_word = key[:4]
    value = key[4:]
    contents = bytearray.fromhex(command_word + value)
    length = len(contents).to_bytes(2, "little")
    return (
        bytearray.fromhex(TX_HEADER) + length + contents + bytearray.fromhex(TX_FOOTER)
    )


def _unwrap_frame(data: bytes, header: str, footer: str) -> bytes:
    """Remove header and footer from a framed message."""
    hdr = bytearray.fromhex(header)
    ftr = bytearray.fromhex(footer)
    if data.startswith(hdr) and data.endswith(ftr):
        length = int.from_bytes(data[len(hdr) : len(hdr) + 2], "little")
        return data[len(hdr) + 2 : len(hdr) + 2 + length]
    return data


def _unwrap_response(data: bytes) -> bytes:
    """Remove header and footer from a response."""
    return _unwrap_frame(data, TX_HEADER, TX_FOOTER)


def _unwrap_intra_frame(data: bytes) -> bytes:
    """Remove header and footer from an intra frame."""
    return _unwrap_frame(data, RX_HEADER, RX_FOOTER)


def _parse_response(key: str, data: bytes) -> bytes:
    """Parse a notification response and verify the ACK."""
    payload = _unwrap_response(data)
    if len(payload) < 2:
        raise OperationError("Response too short")
    expected_ack = (int(key[:4], 16) ^ 0x0001).to_bytes(2, "big")
    command = payload[:2]
    if command != expected_ack:
        raise OperationError(
            f"Unexpected response command {command.hex()} for {key[:4]}"
        )
    return payload[2:]


class BaseDevice:
    """Base representation of a device."""

    def __init__(
        self,
        device: BLEDevice,
        password: str | None = None,
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
        if password is None or password == "":
            self._password_encoded = None
            self._password_words: tuple[str, ...] = ()
        else:
            self._password_encoded = "%08x" % (
                binascii.crc32(password.encode("ascii")) & 0xFFFFFFFF
            )
            self._password_words = _password_to_words(password)
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

    def advertisement_changed(self, advertisement: Advertisement) -> bool:
        """Check if the advertisement has changed."""
        return bool(
            not self._sb_adv_data
            or ble_device_has_changed(self._sb_adv_data.device, advertisement.device)
            or advertisement.data != self._sb_adv_data.data
        )

    def _commandkey(self, key: str) -> str:
        """Perform any necessary modifications to key."""
        return key

    async def _send_command_locked_with_retry(
        self, key: str, command: bytes, retry: int, max_attempts: int
    ) -> bytes | None:
        for attempt in range(max_attempts):
            try:
                return await self._send_command_locked(key, command)
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

    async def _send_command(self, key: str, retry: int | None = None) -> bytes | None:
        """Send command to device and read response."""
        if retry is None:
            retry = self._retry_count
        command = _wrap_command(self._commandkey(key))
        # _LOGGER.debug("%s: Scheduling command %s", self.name, command.hex())
        max_attempts = retry + 1
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        async with self._operation_lock:
            return await self._send_command_locked_with_retry(
                key, command, retry, max_attempts
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
        if self._sb_adv_data:
            return self._sb_adv_data.rssi
        return -127

    @property
    def is_connected(self) -> bool:
        """Return if the BLE client is connected."""
        return bool(self._client and self._client.is_connected)

    async def _ensure_connected(self):
        """Ensure connection to device is established."""
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
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                _LOGGER.debug(
                    "%s: Already connected after obtaining lock, resetting timer; RSSI: %s",
                    self.name,
                    self.rssi,
                )
                self._reset_disconnect_timer()
                return
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

    async def _send_command_locked(self, key: str, command: bytes) -> bytes:
        """Send command to device and read response."""
        await self._ensure_connected()
        try:
            return await self._execute_command_locked(key, command)
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

    def parse_intra_frame(self, data: bytes) -> dict[str, Any] | None:
        """Parse an uplink intra frame.

        Subclasses should override this to handle device specific frames.
        """
        return None

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""
        self._reset_disconnect_timer()
        # Notification is a response to a command
        if data.startswith(bytearray.fromhex(TX_HEADER)):
            if self._notify_future and not self._notify_future.done():
                self._notify_future.set_result(data)
            else:
                _LOGGER.debug(
                    "%s: Received unexpected command response: %s",
                    self.name,
                    data.hex(),
                )
            return
        # Notification is an intra frame from the device
        elif data.startswith(bytearray.fromhex(RX_HEADER)):
            payload = _unwrap_intra_frame(data)
            try:
                #_LOGGER.debug("%s: Received intra frame: %s", self.name, payload.hex())
                parsed = self.parse_intra_frame(payload)
            except Exception as err:  # pragma: no cover - defensive
                _LOGGER.error("%s: Failed to parse intra frame: %s", self.name, err)
            else:
                if parsed and self._update_parsed_data(parsed):
                    self._last_full_update = time.monotonic()
                    self._fire_callbacks()
        else:
            _LOGGER.debug(
                "%s: Received unknown notification: %s", self.name, data.hex()
            )

    async def _start_notify(self) -> None:
        """Start notification."""
        _LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
        await self._client.start_notify(self._read_char, self._notification_handler)

    async def _execute_command_locked(self, key: str, command: bytes) -> bytes:
        """Execute command and read response."""
        assert self._client is not None
        assert self._read_char is not None
        assert self._write_char is not None
        self._notify_future = self.loop.create_future()
        client = self._client

        _LOGGER.debug("%s: Sending command: %s", self.name, key)
        await client.write_gatt_char(self._write_char, command, False)

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

        notify_msg = _parse_response(key, notify_msg_raw)
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
