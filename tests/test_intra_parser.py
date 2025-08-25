"""Tests for intra frame parser and notification handling."""

from __future__ import annotations

import pytest

import logging

from bleak.backends.device import BLEDevice

from custom_components.ld2410.api.devices.ld2410 import LD2410
from custom_components.ld2410.api.const import RX_HEADER, RX_FOOTER
from custom_components.ld2410.api.models import Advertisement


def test_parse_intra_frame_basic() -> None:
    """Ensure basic intra frames are parsed correctly."""
    payload = bytes.fromhex("02aa0101001402002803005500")
    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60)
    )
    result = device.parse_intra_frame(payload)
    assert result == {
        "type": "basic",
        "moving": True,
        "stationary": False,
        "presence": True,
        "move_distance_cm": 1,
        "move_energy": 20,
        "still_distance_cm": 2,
        "still_energy": 40,
        "detect_distance_cm": 3,
    }


@pytest.mark.asyncio
async def test_notification_handler_engineering_frame_updates_data(caplog) -> None:
    """Ensure engineering intra frames update device data and cache."""
    payload_hex = (
        "01aa034e00334e00643e000808123318050403050306000064202627190f1501015500"
    )
    payload = bytes.fromhex(payload_hex)
    length = len(payload).to_bytes(2, "little").hex()
    frame_hex = RX_HEADER + length + payload_hex + RX_FOOTER

    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60)
    )
    advertisement = Advertisement(
        address="AA:BB",
        data={"data": {}},
        device=device._device,
        rssi=-60,
    )
    device.update_from_advertisement(advertisement)

    called = False

    def _cb() -> None:
        nonlocal called
        called = True

    device.subscribe(_cb)
    with caplog.at_level(logging.DEBUG):
        device._notification_handler(0, bytearray.fromhex(frame_hex))

    expected = {
        "type": "engineering",
        "moving": True,
        "stationary": True,
        "presence": True,
        "move_distance_cm": 78,
        "move_energy": 51,
        "still_distance_cm": 78,
        "still_energy": 100,
        "detect_distance_cm": 62,
        "max_move_gate": 8,
        "max_still_gate": 8,
        "move_gate_energy": [18, 51, 24, 5, 4, 3, 5, 3, 6],
        "still_gate_energy": [0, 0, 100, 32, 38, 39, 25, 15, 21],
        "move_gate_energy_0": 18,
        "move_gate_energy_1": 51,
        "move_gate_energy_2": 24,
        "move_gate_energy_3": 5,
        "move_gate_energy_4": 4,
        "move_gate_energy_5": 3,
        "move_gate_energy_6": 5,
        "move_gate_energy_7": 3,
        "move_gate_energy_8": 6,
        "still_gate_energy_0": 0,
        "still_gate_energy_1": 0,
        "still_gate_energy_2": 100,
        "still_gate_energy_3": 32,
        "still_gate_energy_4": 38,
        "still_gate_energy_5": 39,
        "still_gate_energy_6": 25,
        "still_gate_energy_7": 15,
        "still_gate_energy_8": 21,
    }
    assert device.parsed_data == expected
    assert called
    assert await device.get_basic_info() == expected
    assert any(
        rec.message.endswith(str(expected)) and "Updated data" in rec.message
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_notification_handler_initializes_without_advertisement() -> None:
    """Ensure frames populate data even when no advertisement seen."""
    payload_hex = (
        "01aa034e00334e00643e000808123318050403050306000064202627190f1501015500"
    )
    payload = bytes.fromhex(payload_hex)
    length = len(payload).to_bytes(2, "little").hex()
    frame_hex = RX_HEADER + length + payload_hex + RX_FOOTER

    device = LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60)
    )

    device._notification_handler(0, bytearray.fromhex(frame_hex))

    expected = {
        "type": "engineering",
        "moving": True,
        "stationary": True,
        "presence": True,
        "move_distance_cm": 78,
        "move_energy": 51,
        "still_distance_cm": 78,
        "still_energy": 100,
        "detect_distance_cm": 62,
        "max_move_gate": 8,
        "max_still_gate": 8,
        "move_gate_energy": [18, 51, 24, 5, 4, 3, 5, 3, 6],
        "still_gate_energy": [0, 0, 100, 32, 38, 39, 25, 15, 21],
        "move_gate_energy_0": 18,
        "move_gate_energy_1": 51,
        "move_gate_energy_2": 24,
        "move_gate_energy_3": 5,
        "move_gate_energy_4": 4,
        "move_gate_energy_5": 3,
        "move_gate_energy_6": 5,
        "move_gate_energy_7": 3,
        "move_gate_energy_8": 6,
        "still_gate_energy_0": 0,
        "still_gate_energy_1": 0,
        "still_gate_energy_2": 100,
        "still_gate_energy_3": 32,
        "still_gate_energy_4": 38,
        "still_gate_energy_5": 39,
        "still_gate_energy_6": 25,
        "still_gate_energy_7": 15,
        "still_gate_energy_8": 21,
    }

    assert device.parsed_data == expected
    assert await device.get_basic_info() == expected
