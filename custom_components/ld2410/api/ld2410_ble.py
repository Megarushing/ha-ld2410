from __future__ import annotations

import asyncio
import logging
import re
import sys
from collections.abc import Callable
from typing import Any, TypeVar

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.exc import BleakDBusError
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakError,
    BleakNotFoundError,
    establish_connection,
    retry_bluetooth_connection_error,
)

from .const import (
    CHARACTERISTIC_NOTIFY,
    CHARACTERISTIC_WRITE,
    CMD_BT_PASS_DEFAULT,
    CMD_BT_PASS_POST,
    CMD_BT_PASS_PRE,
    CMD_DISABLE_CONFIG,
    CMD_ENABLE_CONFIG,
    CMD_ENABLE_ENGINEERING_MODE,
    MOVING_TARGET,
    STATIC_TARGET,
    engineering_frame_regex,
    frame_regex,
)
from .exceptions import CharacteristicMissingError
from .models import LD2410BLEState

BLEAK_BACKOFF_TIME = 0.25

__version__ = "0.0.0"


WrapFuncType = TypeVar("WrapFuncType", bound=Callable[..., Any])

RETRY_BACKOFF_EXCEPTIONS = (BleakDBusError,)

_LOGGER = logging.getLogger(__name__)

DEFAULT_ATTEMPTS = sys.maxsize


class LD2410BLE:
    def __init__(
        self,
        ble_device: BLEDevice,
        advertisement_data: AdvertisementData | None = None,
        password: bytes = CMD_BT_PASS_DEFAULT,
    ) -> None:
        """Init the LD2410BLE."""
        self._ble_device = ble_device
        self._advertisement_data = advertisement_data
        self._password = password
        self._operation_lock = asyncio.Lock()
        self._state = LD2410BLEState()
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._client: BleakClientWithServiceCache | None = None
        self._expected_disconnect = False
        self.loop = asyncio.get_running_loop()
        self._callbacks: list[Callable[[LD2410BLEState], None]] = []
        self._disconnected_callbacks: list[Callable[[], None]] = []
        self._buf = b""

    def set_ble_device_and_advertisement_data(
        self, ble_device: BLEDevice, advertisement_data: AdvertisementData
    ) -> None:
        """Set the ble device."""
        self._ble_device = ble_device
        self._advertisement_data = advertisement_data

    @property
    def address(self) -> str:
        """Return the address."""
        return self._ble_device.address

    @property
    def _address(self) -> str:
        """Return the address."""
        return self._ble_device.address

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self._ble_device.name or self._ble_device.address

    @property
    def rssi(self) -> int | None:
        """Get the rssi of the device."""
        if self._advertisement_data:
            return self._advertisement_data.rssi
        return None

    @property
    def state(self) -> LD2410BLEState:
        """Return the state."""
        return self._state

    @property
    def is_moving(self) -> bool:
        return self._state.is_moving

    @property
    def is_static(self) -> bool:
        return self._state.is_static

    @property
    def moving_target_distance(self) -> int:
        return self._state.moving_target_distance

    @property
    def moving_target_energy(self) -> int:
        return self._state.moving_target_energy

    @property
    def static_target_distance(self) -> int:
        return self._state.static_target_distance

    @property
    def static_target_energy(self) -> int:
        return self._state.static_target_energy

    @property
    def detection_distance(self) -> int:
        return self._state.detection_distance

    @property
    def max_motion_gates(self) -> int:
        assert self._state.max_motion_gates is not None  # nosec
        return self._state.max_motion_gates

    @property
    def max_static_gates(self) -> int:
        assert self._state.max_static_gates is not None  # nosec
        return self._state.max_static_gates

    @property
    def motion_energy_gates(self) -> list[int]:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates

    @property
    def motion_energy_gate_0(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[0]

    @property
    def motion_energy_gate_1(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[1]

    @property
    def motion_energy_gate_2(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[2]

    @property
    def motion_energy_gate_3(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[3]

    @property
    def motion_energy_gate_4(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[4]

    @property
    def motion_energy_gate_5(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[5]

    @property
    def motion_energy_gate_6(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[6]

    @property
    def motion_energy_gate_7(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[7]

    @property
    def motion_energy_gate_8(self) -> int:
        assert self._state.motion_energy_gates is not None  # nosec
        return self._state.motion_energy_gates[8]

    @property
    def static_energy_gates(self) -> list[int]:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates

    @property
    def static_energy_gate_0(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[0]

    @property
    def static_energy_gate_1(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[1]

    @property
    def static_energy_gate_2(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[2]

    @property
    def static_energy_gate_3(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[3]

    @property
    def static_energy_gate_4(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[4]

    @property
    def static_energy_gate_5(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[5]

    @property
    def static_energy_gate_6(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[6]

    @property
    def static_energy_gate_7(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[7]

    @property
    def static_energy_gate_8(self) -> int:
        assert self._state.static_energy_gates is not None  # nosec
        return self._state.static_energy_gates[8]

    async def stop(self) -> None:
        """Stop the LD2410BLE."""
        _LOGGER.debug("%s: Stop", self.name)
        await self._execute_disconnect()

    def _fire_callbacks(self) -> None:
        """Fire the callbacks."""
        for callback in self._callbacks:
            callback(self._state)

    def register_callback(
        self, callback: Callable[[LD2410BLEState], None]
    ) -> Callable[[], None]:
        """Register a callback to be called when the state changes."""

        def unregister_callback() -> None:
            self._callbacks.remove(callback)

        self._callbacks.append(callback)
        return unregister_callback

    def _fire_disconnected_callbacks(self) -> None:
        """Fire the callbacks."""
        for callback in self._disconnected_callbacks:
            callback()

    def register_disconnected_callback(
        self, callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback to be called when the state changes."""

        def unregister_callback() -> None:
            self._disconnected_callbacks.remove(callback)

        self._disconnected_callbacks.append(callback)
        return unregister_callback

    async def initialise(self) -> None:
        _LOGGER.debug("%s: Sending configuration commands", self.name)
        await self._send_command(CMD_BT_PASS_PRE + self._password + CMD_BT_PASS_POST)
        await asyncio.sleep(0.1)
        await self._send_command(CMD_ENABLE_CONFIG)
        await asyncio.sleep(0.1)
        await self._send_command(CMD_ENABLE_ENGINEERING_MODE)
        await asyncio.sleep(0.1)
        await self._send_command(CMD_DISABLE_CONFIG)
        await asyncio.sleep(0.1)

        _LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
        if self._client is not None:
            await self._client.start_notify(
                CHARACTERISTIC_NOTIFY, self._notification_handler
            )

    async def _ensure_connected(self) -> None:
        """Ensure connection to device is established."""
        if self._connect_lock.locked():
            _LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        if self._client and self._client.is_connected:
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                return
            _LOGGER.debug("%s: Connecting; RSSI: %s", self.name, self.rssi)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self.name,
                self._disconnected,
                use_services_cache=True,
                ble_device_callback=lambda: self._ble_device,
            )
            _LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)

            self._client = client

    async def _reconnect(self) -> None:
        """Attempt a reconnect"""
        _LOGGER.debug("ensuring connection")
        try:
            await self._ensure_connected()
            _LOGGER.debug("ensured connection - initialising")
            await self.initialise()
        except (BleakNotFoundError, BleakError) as error:
            _LOGGER.debug("failed to ensure connection - backing off: %s", error)
            await asyncio.sleep(BLEAK_BACKOFF_TIME)
            _LOGGER.debug("reconnecting again")
            asyncio.create_task(self._reconnect())

    def intify(self, state: bytes) -> int:
        return int.from_bytes(state, byteorder="little")

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""
        _LOGGER.debug("%s: Notification received: %s", self.name, data.hex())

        self._buf += data
        msg = re.search(frame_regex, self._buf)
        if msg:
            self._buf = self._buf[msg.end() :]  # noqa: E203
            target_state = msg.group("target_state")
            engineering_data = msg.group("engineering_data")

            target_state_int = self.intify(target_state)
            is_moving = bool(target_state_int & MOVING_TARGET)
            is_static = bool(target_state_int & STATIC_TARGET)
            moving_target_distance = self.intify(msg.group("moving_target_distance"))
            moving_target_energy = self.intify(msg.group("moving_target_energy"))
            static_target_distance = self.intify(msg.group("static_target_distance"))
            static_target_energy = self.intify(msg.group("static_target_energy"))
            detection_distance = self.intify(msg.group("detection_distance"))

            max_motion_gates = None
            max_static_gates = None
            motion_energy_gates = None
            static_energy_gates = None
            if engineering_data:
                em = re.match(engineering_frame_regex, engineering_data)
                if em:
                    max_motion_gates = self.intify(em.group("maximum_motion_gates"))
                    max_static_gates = self.intify(em.group("maximum_static_gates"))
                    motion_energy_gates = [x for x in em.group("motion_energy_gates")]
                    static_energy_gates = [x for x in em.group("static_energy_gates")]

            self._state = LD2410BLEState(
                is_moving=is_moving,
                is_static=is_static,
                moving_target_distance=moving_target_distance,
                moving_target_energy=moving_target_energy,
                static_target_distance=static_target_distance,
                static_target_energy=static_target_energy,
                detection_distance=detection_distance,
                max_motion_gates=max_motion_gates,
                max_static_gates=max_static_gates,
                motion_energy_gates=motion_energy_gates,
                static_energy_gates=static_energy_gates,
            )

            self._fire_callbacks()

        _LOGGER.debug(
            "%s: Notification received; RSSI: %s: %s %s",
            self.name,
            self.rssi,
            data.hex(),
            self._state,
        )

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        self._fire_disconnected_callbacks()
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
        asyncio.create_task(self._reconnect())

    def _disconnect(self) -> None:
        """Disconnect from device."""
        asyncio.create_task(self._execute_timed_disconnect())

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection."""
        _LOGGER.debug(
            "%s: Disconnecting",
            self.name,
        )
        await self._execute_disconnect()

    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        async with self._connect_lock:
            client = self._client
            self._expected_disconnect = True
            self._client = None
            if client and client.is_connected:
                await client.stop_notify(CHARACTERISTIC_NOTIFY)
                await client.disconnect()

    @retry_bluetooth_connection_error(DEFAULT_ATTEMPTS)
    async def _send_command_locked(self, commands: list[bytes]) -> None:
        """Send command to device and read response."""
        try:
            await self._execute_command_locked(commands)
        except BleakDBusError as ex:
            # Disconnect so we can reset state and try again
            await asyncio.sleep(BLEAK_BACKOFF_TIME)
            _LOGGER.debug(
                "%s: RSSI: %s; Backing off %ss; Disconnecting due to error: %s",
                self.name,
                self.rssi,
                BLEAK_BACKOFF_TIME,
                ex,
            )
            await self._execute_disconnect()
            raise
        except BleakError as ex:
            # Disconnect so we can reset state and try again
            _LOGGER.debug(
                "%s: RSSI: %s; Disconnecting due to error: %s", self.name, self.rssi, ex
            )
            await self._execute_disconnect()
            raise

    async def _send_command(
        self, commands: list[bytes] | bytes, retry: int | None = None
    ) -> None:
        """Send command to device and read response."""
        await self._ensure_connected()
        if not isinstance(commands, list):
            commands = [commands]
        await self._send_command_while_connected(commands, retry)

    async def _send_command_while_connected(
        self, commands: list[bytes], retry: int | None = None
    ) -> None:
        """Send command to device and read response."""
        _LOGGER.debug(
            "%s: Sending commands %s",
            self.name,
            [command.hex() for command in commands],
        )
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        async with self._operation_lock:
            try:
                await self._send_command_locked(commands)
                return
            except BleakNotFoundError:
                _LOGGER.error(
                    "%s: device not found, no longer in range, or poor RSSI: %s",
                    self.name,
                    self.rssi,
                    exc_info=True,
                )
                raise
            except CharacteristicMissingError as ex:
                _LOGGER.debug(
                    "%s: characteristic missing: %s; RSSI: %s",
                    self.name,
                    ex,
                    self.rssi,
                    exc_info=True,
                )
                raise
            except BLEAK_EXCEPTIONS:
                _LOGGER.debug("%s: communication failed", self.name, exc_info=True)
                raise

        raise RuntimeError("Unreachable")

    async def _execute_command_locked(self, commands: list[bytes]) -> None:
        """Execute command and read response."""
        assert self._client is not None  # nosec
        for command in commands:
            await self._client.write_gatt_char(CHARACTERISTIC_WRITE, command, False)
