"""Regression tests for the bugs found in the 2026-10 code review."""

import asyncio
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from bleak.backends.device import BLEDevice
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.ld2410.api.const import CMD_ENABLE_CFG, CMD_END_CFG
from custom_components.ld2410.api.devices.device import OperationError
from custom_components.ld2410.api.devices.ld2410 import LD2410
from custom_components.ld2410.const import (
    CONF_RETRY_COUNT,
    CONF_SAVED_MOVE_SENSITIVITY,
    CONF_SAVED_STILL_SENSITIVITY,
    DOMAIN,
)
from custom_components.ld2410.diagnostics import async_get_config_entry_diagnostics

from . import LD2410b_SERVICE_INFO

try:
    from tests.common import MockConfigEntry
except ImportError:  # Home Assistant <2023.9
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import inject_bluetooth_service_info
except ImportError:  # Home Assistant <2023.9
    from .mocks import inject_bluetooth_service_info

API = "custom_components.ld2410.api"


def _device(**kwargs) -> LD2410:
    return LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        **kwargs,
    )


class _ScriptedDevice(LD2410):
    """Device whose command responses come from a list; always connected."""

    def __init__(self, responses: list[bytes]) -> None:
        super().__init__(
            device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60)
        )
        self._responses = responses
        self.raw_commands: list[str] = []

    async def _send_command(self, raw_command, retry=None, *, wait_for_response=None):
        self.raw_commands.append(raw_command)
        await asyncio.sleep(0)  # let other tasks run, to expose interleaving
        return self._responses.pop(0)

    async def _ensure_connected(self) -> bool:
        return False


def _entry(**data) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "name": "test-name",
            "password": "test-password",
            "sensor_type": "ld2410",
            **data,
        },
        unique_id="aabbccddeeff",
    )


async def _setup(hass: HomeAssistant, stack: ExitStack, entry: MockConfigEntry):
    """Load the integration with a fake, already-connected device."""
    await async_setup_component(hass, DOMAIN, {})
    await async_setup_component(hass, "persistent_notification", {})
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
    entry.add_to_hass(hass)
    stack.enter_context(patch(f"{API}.close_stale_connections_by_address"))
    stack.enter_context(
        patch(
            f"{API}.devices.device.BaseDevice._ensure_connected",
            AsyncMock(return_value=True),
        )
    )
    stack.enter_context(patch(f"{API}.LD2410._on_connect", AsyncMock()))
    stack.enter_context(patch("custom_components.ld2410.helpers.async_call_later"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)
    await hass.async_block_till_done()
    return entry.runtime_data.device


# 1. Initial connection failure is retried ------------------------------------


async def test_initial_connect_failure_schedules_reconnect() -> None:
    """A failed first connect must keep retrying, not leave the device silent."""
    device = _device(password="HiLink")
    device._ensure_connected = AsyncMock(side_effect=TimeoutError("busy"))
    device.schedule_reconnect = lambda: setattr(device, "retry_scheduled", True)

    device.start_connecting()
    await device._initial_connect_task

    assert device.retry_scheduled


async def test_unload_cancels_initial_connect(hass: HomeAssistant) -> None:
    """Unloading during the first connect must not leave the task running."""
    with ExitStack() as stack:
        entry = _entry()
        device = await _setup(hass, stack, entry)
        device._initial_connect_task = asyncio.create_task(asyncio.sleep(3600))
        task = device._initial_connect_task
        assert await hass.config_entries.async_unload(entry.entry_id)
    assert task.cancelled()


# 2. Diagnostics redact the password ------------------------------------------


async def test_diagnostics_redacts_password(hass: HomeAssistant) -> None:
    """The Bluetooth password must not appear in downloaded diagnostics."""
    with ExitStack() as stack:
        entry = _entry(password="s3cret")
        await _setup(hass, stack, entry)
        result = await async_get_config_entry_diagnostics(hass, entry)
    assert "s3cret" not in json.dumps(result, default=str)
    assert result["entry"]["data"][CONF_PASSWORD] == "**REDACTED**"


# 3. Options flow keeps saved sensitivities -----------------------------------


async def test_options_flow_keeps_saved_sensitivities(hass: HomeAssistant) -> None:
    """Submitting Configure must not erase the saved gate sensitivities."""
    entry = _entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry,
        options={
            CONF_RETRY_COUNT: 3,
            CONF_SAVED_MOVE_SENSITIVITY: [50] * 9,
            CONF_SAVED_STILL_SENSITIVITY: [40] * 9,
        },
    )
    with patch("custom_components.ld2410.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_RETRY_COUNT: 5}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_RETRY_COUNT] == 5
    assert entry.options[CONF_SAVED_MOVE_SENSITIVITY] == [50] * 9
    assert entry.options[CONF_SAVED_STILL_SENSITIVITY] == [40] * 9


async def test_options_flow_rejects_negative_retry(hass: HomeAssistant) -> None:
    """A negative retry count would make every command fail."""
    entry = _entry()
    entry.add_to_hass(hass)
    with patch("custom_components.ld2410.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        with pytest.raises(InvalidData):
            await hass.config_entries.options.async_configure(
                result["flow_id"], user_input={CONF_RETRY_COUNT: -1}
            )


# 4. Auto sensitivities accepts "completed" -----------------------------------


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_auto_sensitivities_stops_on_completed(hass: HomeAssistant) -> None:
    """Status 2 (completed) must end the wait and read the new values."""
    with ExitStack() as stack:
        await _setup(hass, stack, _entry())
        stack.enter_context(patch(f"{API}.LD2410.cmd_auto_thresholds", AsyncMock()))
        query = stack.enter_context(
            patch(
                f"{API}.LD2410.cmd_query_auto_thresholds",
                AsyncMock(side_effect=[1, 1, 2]),
            )
        )
        read = stack.enter_context(
            patch(
                f"{API}.LD2410.cmd_read_params",
                AsyncMock(
                    return_value={
                        "move_gate_sensitivity": [1] * 9,
                        "still_gate_sensitivity": [2] * 9,
                    }
                ),
            )
        )
        stack.enter_context(
            patch("custom_components.ld2410.button.asyncio.sleep", AsyncMock())
        )
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.test_name_auto_sensitivities"},
            blocking=True,
        )
    assert query.await_count == 3
    read.assert_awaited_once()


# 5. Cancellation is not swallowed --------------------------------------------


async def test_external_cancel_propagates() -> None:
    """A timeout or unload cancelling a command must stay a cancellation."""
    device = _device()
    device._ensure_connected = AsyncMock(return_value=False)
    started = asyncio.Event()

    async def _hang(*args):
        started.set()
        await asyncio.sleep(3600)

    device._send_command_locked_with_retry = _hang
    task = asyncio.create_task(device._send_command("FF00"))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_disconnect_cancel_becomes_operation_error() -> None:
    """A command cut off by our own disconnect still reports a clean error."""
    device = _device()
    device._ensure_connected = AsyncMock(return_value=False)
    started = asyncio.Event()

    async def _hang(*args):
        started.set()
        await asyncio.sleep(3600)

    device._send_command_locked_with_retry = _hang
    task = asyncio.create_task(device._send_command("FF00"))
    await started.wait()
    device._clear_locked_commands()
    with pytest.raises(OperationError, match="Device disconnecting"):
        await task


# 6. Absence delay keeps the configured max gates -----------------------------


async def test_engineering_frame_does_not_overwrite_max_gates() -> None:
    """Frames report their own gate count; it must not replace the config."""
    device = _ScriptedDevice([b"\x00\x00\x01\x00\x00@", b"\x00\x00", b"\x00\x00"])
    device._update_parsed_data(
        {"max_move_gate": 4, "max_still_gate": 3, "absence_delay": 5}
    )
    frame = device._parse_uplink_frame(
        bytes.fromhex("01aa031e00641e00641e000808")
        + bytes(9)
        + bytes(9)
        + bytes.fromhex("00005500")
    )
    device._update_parsed_data(frame)

    await device.cmd_set_absence_delay(10)

    payload = device.raw_commands[1]
    assert "0000" + (4).to_bytes(4, "little").hex() in payload
    assert "0100" + (3).to_bytes(4, "little").hex() in payload


# 7. New password is never stored in plain text -------------------------------


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_new_password_state_is_masked_and_cleared(hass: HomeAssistant) -> None:
    """The text state goes to history, so it must never hold the password."""
    with ExitStack() as stack:
        entry = _entry()
        device = await _setup(hass, stack, entry)
        await hass.services.async_call(
            "text",
            "set_value",
            {"entity_id": "text.test_name_new_password", "value": "abcd12"},
            blocking=True,
        )
        assert hass.states.get("text.test_name_new_password").state == "******"

        async def _accept(password):
            device._password_words = ()
            device.password_is = lambda pw: pw == password

        stack.enter_context(
            patch.object(device, "cmd_set_bluetooth_password", side_effect=_accept)
        )
        stack.enter_context(patch.object(device, "cmd_reboot", AsyncMock()))
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.test_name_change_password"},
            blocking=True,
        )
        assert entry.runtime_data.new_password == ""


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_password_saved_when_end_config_fails(hass: HomeAssistant) -> None:
    """If the device took the new password, save it even when a later step fails."""
    with ExitStack() as stack:
        entry = _entry(password="old123")
        device = await _setup(hass, stack, entry)
        entry.runtime_data.new_password = "abcd12"

        async def _accept_then_fail(password):
            device.password_is = lambda pw: pw == password
            raise OperationError("Failed to end configuration")

        stack.enter_context(
            patch.object(
                device, "cmd_set_bluetooth_password", side_effect=_accept_then_fail
            )
        )
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.test_name_change_password"},
                blocking=True,
            )
    assert entry.data[CONF_PASSWORD] == "abcd12"


# 8. BLE errors become friendly errors ----------------------------------------


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_ble_timeout_is_translated(hass: HomeAssistant) -> None:
    """A BLE timeout must surface as the integration's operation error."""
    with ExitStack() as stack:
        device = await _setup(hass, stack, _entry())
        stack.enter_context(
            patch.object(device, "cmd_reboot", AsyncMock(side_effect=TimeoutError))
        )
        with pytest.raises(HomeAssistantError) as err:
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": "button.test_name_reboot_device"},
                blocking=True,
            )
    assert err.value.translation_key == "operation_error"


async def test_config_flow_password_step_cannot_connect(hass: HomeAssistant) -> None:
    """Losing the device during the password step shows an error, not a crash."""
    from custom_components.ld2410.config_flow import LD2410ConfigFlow

    flow = LD2410ConfigFlow()
    flow.hass = hass
    flow._discovered_adv = type(
        "Adv",
        (),
        {
            "device": BLEDevice(address="AA:BB", name="t", details=None, rssi=-60),
            "address": "AA:BB",
            "data": {"modelFriendlyName": "HLK-LD2410", "modelName": "ld2410"},
        },
    )()
    with (
        patch(
            f"{API}.LD2410.cmd_send_bluetooth_password",
            AsyncMock(side_effect=TimeoutError),
        ),
        patch(f"{API}.LD2410.async_disconnect", AsyncMock()),
    ):
        result = await flow.async_step_password({CONF_PASSWORD: "HiLink"})
    assert result["errors"] == {"base": "cannot_connect"}


# 9. Config sessions do not interleave and always close -----------------------


async def test_config_sessions_do_not_interleave() -> None:
    """Two commands at once must each run ENABLE, command, END in one block."""
    ok_enable = b"\x00\x00\x01\x00\x00@"
    device = _ScriptedDevice([ok_enable, b"\x00\x00", b"\x00\x00"] * 2)
    device._update_parsed_data(
        {
            "move_gate_sensitivity": [0] * 9,
            "max_move_gate": 8,
            "max_still_gate": 8,
            "absence_delay": 5,
        }
    )
    await asyncio.gather(
        device.cmd_set_light_config(threshold=10),
        device.cmd_set_absence_delay(5),
    )
    sessions = [device.raw_commands[i : i + 3] for i in (0, 3)]
    for session in sessions:
        assert session[0] == CMD_ENABLE_CFG + "0001"
        assert session[2] == CMD_END_CFG


async def test_config_session_closed_on_error() -> None:
    """A rejected command must still end config mode, or streaming stops."""
    device = _ScriptedDevice([b"\x00\x00\x01\x00\x00@", b"\x01\x00", b"\x00\x00"])
    device._update_parsed_data(
        {"max_move_gate": 8, "max_still_gate": 8, "absence_delay": 5}
    )
    with pytest.raises(OperationError):
        await device.cmd_set_absence_delay(5)
    assert device.raw_commands[-1] == CMD_END_CFG


# 10. Sensitivity slider never sends a guessed value --------------------------


async def test_gate_sensitivity_refuses_unknown_pair() -> None:
    """Without the other value known, sending 0 would wipe it on the device."""
    device = _ScriptedDevice([b"\x00\x00\x01\x00\x00@", b"\x00\x00"])
    with pytest.raises(OperationError):
        await device.cmd_set_gate_sensitivity(0, move=30)
    assert device.raw_commands == [CMD_ENABLE_CFG + "0001", CMD_END_CFG]


# 11. Entities refresh right after a setting is written -----------------------


async def test_set_command_fires_callbacks() -> None:
    """The UI must show a new setting at once, not after the next frame."""
    device = _ScriptedDevice([b"\x00\x00\x01\x00\x00@", b"\x00\x00", b"\x00\x00"])
    device._update_parsed_data(
        {"max_move_gate": 8, "max_still_gate": 8, "absence_delay": 5}
    )
    fired = []
    device.subscribe(lambda: fired.append(True))
    await device.cmd_set_absence_delay(42)
    assert fired


# 12. Config and options screens have their strings ---------------------------


def test_translations_cover_config_and_options() -> None:
    """Custom integrations read translations/en.json, not strings.json."""
    path = Path(__file__).parents[1] / "custom_components/ld2410/translations/en.json"
    en = json.loads(path.read_text())
    assert "password" in en["config"]["step"]
    assert {"wrong_password", "cannot_connect"} <= set(en["config"]["error"])
    assert "not_supported" in en["config"]["abort"]
    assert "retry_count" in en["options"]["step"]["init"]["data"]


# Max gates (new number entities) -------------------------------------------


def _gates_device() -> _ScriptedDevice:
    device = _ScriptedDevice([b"\x00\x00\x01\x00\x00@", b"\x00\x00", b"\x00\x00"])
    device._update_parsed_data(
        {"max_move_gate": 8, "max_still_gate": 6, "absence_delay": 30}
    )
    return device


async def test_set_max_move_gate_keeps_other_values() -> None:
    """Changing one max gate re-sends the other gate and the absence delay."""
    device = _gates_device()
    await device.cmd_set_max_gates(move_gate=4)
    payload = device.raw_commands[1]
    assert payload == (
        "6000"
        + "0000"
        + (4).to_bytes(4, "little").hex()
        + "0100"
        + (6).to_bytes(4, "little").hex()
        + "0200"
        + (30).to_bytes(4, "little").hex()
    )
    assert device.parsed_data["max_move_gate"] == 4
    assert device.parsed_data["max_still_gate"] == 6


async def test_set_max_gate_refused_when_settings_unknown() -> None:
    """Without the current values, sending guesses would overwrite them."""
    device = _ScriptedDevice([b"\x00\x00\x01\x00\x00@", b"\x00\x00"])
    with pytest.raises(OperationError):
        await device.cmd_set_max_gates(still_gate=4)
    assert device.raw_commands == [CMD_ENABLE_CFG + "0001", CMD_END_CFG]


@pytest.mark.parametrize("gate", [1, 9])
async def test_set_max_gate_range(gate: int) -> None:
    """The radar accepts max gates 2..8 only."""
    with pytest.raises(ValueError):
        await _gates_device().cmd_set_max_gates(move_gate=gate)


async def test_max_gate_number_entity(hass: HomeAssistant) -> None:
    """The Max still gate control calls the device with only that gate."""
    eid = "number.test_name_max_still_gate"
    with ExitStack() as stack:
        entry = _entry()
        await _setup(hass, stack, entry)
        er.async_get(hass).async_update_entity(eid, disabled_by=None)  # off by default
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        send = stack.enter_context(
            patch.object(entry.runtime_data.device, "cmd_set_max_gates", AsyncMock())
        )
        await hass.services.async_call(
            "number", "set_value", {"entity_id": eid, "value": 5}, blocking=True
        )
    send.assert_awaited_once_with(still_gate=5)


# Concurrent changes to settings that share one command (Codex review, #102) --

OK_SESSION = [b"\x00\x00\x01\x00\x00@", b"\x00\x00", b"\x00\x00"]


async def test_concurrent_max_gates_do_not_undo_each_other() -> None:
    """Setting both max gates at once must keep both new values."""
    device = _ScriptedDevice(OK_SESSION * 2)
    device._update_parsed_data(
        {"max_move_gate": 8, "max_still_gate": 8, "absence_delay": 5}
    )
    await asyncio.gather(
        device.cmd_set_max_gates(move_gate=4), device.cmd_set_max_gates(still_gate=3)
    )
    last = device.raw_commands[4]
    assert "0000" + (4).to_bytes(4, "little").hex() in last
    assert "0100" + (3).to_bytes(4, "little").hex() in last
    assert (
        device.parsed_data["max_move_gate"],
        device.parsed_data["max_still_gate"],
    ) == (4, 3)


async def test_concurrent_gate_sensitivities_do_not_undo_each_other() -> None:
    """MG3 and SG3 share one command; changing both at once keeps both."""
    device = _ScriptedDevice(OK_SESSION * 2)
    device._update_parsed_data(
        {"move_gate_sensitivity": [50] * 9, "still_gate_sensitivity": [40] * 9}
    )
    await asyncio.gather(
        device.cmd_set_gate_sensitivity(3, move=20),
        device.cmd_set_gate_sensitivity(3, still=10),
    )
    assert device.parsed_data["move_gate_sensitivity"][3] == 20
    assert device.parsed_data["still_gate_sensitivity"][3] == 10


async def test_concurrent_light_settings_do_not_undo_each_other() -> None:
    """Light mode and threshold share one command; both changes must stick."""
    device = _ScriptedDevice(OK_SESSION * 2)
    device._update_parsed_data(
        {"light_function": 0, "light_threshold": 128, "light_out_level": 0}
    )
    await asyncio.gather(
        device.cmd_set_light_config(mode=1), device.cmd_set_light_config(threshold=50)
    )
    assert (
        device.parsed_data["light_function"],
        device.parsed_data["light_threshold"],
    ) == (1, 50)
