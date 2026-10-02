"""Tests for uplink frame arrival tracking."""

from __future__ import annotations

from bleak.backends.device import BLEDevice

from custom_components.ld2410.api.const import RX_FOOTER, RX_HEADER, TX_HEADER
from custom_components.ld2410.api.devices.ld2410 import LD2410

ENGINEERING_PAYLOAD = (
    "01aa034e00334e00643e000808123318050403050306000064202627190f1501015500"
)


def _make_device() -> LD2410:
    return LD2410(
        device=BLEDevice(address="AA:BB", name="test", details=None, rssi=-60)
    )


def _frame(payload_hex: str) -> bytearray:
    payload = bytes.fromhex(payload_hex)
    length = len(payload).to_bytes(2, "little").hex()
    return bytearray.fromhex(RX_HEADER + length + payload_hex + RX_FOOTER)


def test_last_frame_time_starts_unset() -> None:
    """A device that never received a frame reports no timestamp."""
    assert _make_device().last_frame_time is None


def test_uplink_frame_stamps_last_frame_time() -> None:
    """An uplink frame records its arrival time."""
    device = _make_device()

    device._handle_notification(_frame(ENGINEERING_PAYLOAD))

    assert device.last_frame_time is not None


def test_identical_frames_still_stamp_arrival() -> None:
    """Repeated identical frames must re-stamp arrival.

    Regression: a still room streams byte-identical frames, which leave parsed
    data unchanged. Arrival tracking must not be tied to data changing, or a
    healthy device is indistinguishable from a stalled one.
    """
    device = _make_device()
    frame = _frame(ENGINEERING_PAYLOAD)

    device._handle_notification(frame)
    first = device.last_frame_time

    device._last_frame_time = first - 10  # simulate time passing
    device._handle_notification(frame)

    assert device.last_frame_time > first - 10


def test_unparseable_uplink_frame_still_stamps() -> None:
    """Arrival is recorded even when the payload cannot be parsed.

    An unparseable frame still proves the device is streaming.
    """
    device = _make_device()

    # Second payload byte is not 0xAA, so _parse_uplink_frame returns None.
    device._handle_notification(_frame("01bb0000"))

    assert device.last_frame_time is not None


def test_command_response_does_not_stamp() -> None:
    """Command responses must not mask a dead uplink stream."""
    device = _make_device()

    device._handle_notification(bytearray.fromhex(TX_HEADER + "0400" + "0000" + "0000"))

    assert device.last_frame_time is None
