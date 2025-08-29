from __future__ import annotations

import asyncio

import pytest
from bleak.backends.device import BLEDevice

from custom_components.ld2410.api.devices.device import (
    BaseDevice,
    OperationError,
    _handle_timeout,
    _merge_data,
)
from custom_components.ld2410.api.devices.ld2410 import LD2410, _unwrap_frame
from custom_components.ld2410.api.const import CMD_BT_GET_PERMISSION
from custom_components.ld2410.api.models import Advertisement


def test_merge_data_recurses() -> None:
    """Nested dictionaries are merged recursively."""
    original = {"a": {"b": 1}}
    new = {"a": {"c": 2}, "d": None}
    assert _merge_data(original, new) == {"a": {"b": 1, "c": 2}, "d": None}


@pytest.mark.asyncio
async def test_handle_timeout_sets_exception() -> None:
    """Timeout handler sets TimeoutError on unfinished future."""
    fut: asyncio.Future[None] = asyncio.get_event_loop().create_future()
    _handle_timeout(fut)
    with pytest.raises(asyncio.TimeoutError):
        await fut


def test_unwrap_frame_returns_input_if_no_markers() -> None:
    """_unwrap_frame returns data when header/footer missing."""
    data = bytes.fromhex("00112233")
    assert _unwrap_frame(data, "fdfc", "0403") == data


def test_parse_response_unexpected_ack() -> None:
    """Unexpected ACK raises OperationError."""
    raw = bytes.fromhex("fdfcfbfa0400a802000004030201")
    dev = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60),
        password=None,
    )
    with pytest.raises(OperationError):
        dev._parse_response(CMD_BT_GET_PERMISSION, raw)


@pytest.mark.asyncio
async def test_advertisement_changed_detects_changes() -> None:
    """advertisement_changed returns True when advertisement differs."""
    dev = BaseDevice(device=BLEDevice(address="AA:BB", name="d", details=None))
    adv1 = Advertisement("AA:BB", {"k": 1}, dev._device, -40)
    assert dev.advertisement_changed(adv1)
    dev._sb_adv_data = adv1
    adv2 = Advertisement("AA:BB", {"k": 2}, dev._device, -40)
    assert dev.advertisement_changed(adv2)
