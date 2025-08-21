"""LD2410 Device Consts Library."""

from __future__ import annotations

from ..enum import StrEnum

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

CHARACTERISTIC_NOTIFY = "0000fff1-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_WRITE = "0000fff2-0000-1000-8000-00805f9b34fb"

CMD_BT_PASS_PRE = b"\xfd\xfc\xfb\xfa\x08\x00\xa8\x00"
CMD_BT_PASS_DEFAULT = b"HiLink"
CMD_BT_PASS_POST = b"\x04\x03\x02\x01"
CMD_ENABLE_CONFIG = b"\xfd\xfc\xfb\xfa\x04\x00\xff\x00\x01\x00\x04\x03\x02\x01"
CMD_ENABLE_ENGINEERING_MODE = b"\xfd\xfc\xfb\xfa\x02\x00b\x00\x04\x03\x02\x01"
CMD_DISABLE_CONFIG = b"\xfd\xfc\xfb\xfa\x02\x00\xfe\x00\x04\x03\x02\x01"

MOVING_TARGET = 1
STATIC_TARGET = 2

frame_start = b"\xf4\xf3\xf2\xf1"
frame_length = b"(?P<length>..)"
frame_engineering_mode = b"(?P<engineering>\x01|\x02)"
frame_head = b"\xaa"
frame_target_state = b"(?P<target_state>\x00|\x01|\x02|\x03)"
frame_moving_target_distance = b"(?P<moving_target_distance>..)"
frame_moving_target_energy = b"(?P<moving_target_energy>.)"
frame_static_target_distance = b"(?P<static_target_distance>..)"
frame_static_target_energy = b"(?P<static_target_energy>.)"
frame_detection_distance = b"(?P<detection_distance>..)"
frame_engineering_data = b"(?P<engineering_data>.+?)?"
frame_tail = b"\x55"
frame_check = b"\x00"
frame_end = b"\xf8\xf7\xf6\xf5"

frame_maximum_motion_gates = b"(?P<maximum_motion_gates>.)"
frame_maximum_static_gates = b"(?P<maximum_static_gates>.)"
frame_motion_energy_gates = b"(?P<motion_energy_gates>.{9})"
frame_static_energy_gates = b"(?P<static_energy_gates>.{9})"
frame_additional_information = b"(?P<additional_information>.*)"

frame_regex = (
        frame_start
        + frame_length
        + frame_engineering_mode
        + frame_head
        + frame_target_state
        + frame_moving_target_distance
        + frame_moving_target_energy
        + frame_static_target_distance
        + frame_static_target_energy
        + frame_detection_distance
        + frame_engineering_data
        + frame_tail
        + frame_check
        + frame_end
)

engineering_frame_regex = (
        frame_maximum_motion_gates
        + frame_maximum_static_gates
        + frame_motion_energy_gates
        + frame_static_energy_gates
        + frame_additional_information
)


class LD2410ApiError(RuntimeError):
    """Raised when an API call fails."""


class LD2410AuthenticationError(RuntimeError):
    """Raised when authentication fails."""


class LD2410AccountConnectionError(RuntimeError):
    """Raised when connection to the LD2410 account fails."""


class LD2410Model(StrEnum):
    """LD2410 device models."""

    CONTACT_SENSOR = "WoContact"
    MOTION_SENSOR = "WoPresence"
    LD2410 = "HLK-LD2410B"

    RELAY_SWITCH_2PM = "RELAY_SWITCH_2PM"
    RELAY_SWITCH_1PM = "RELAY_SWITCH_1PM"
    GARAGE_DOOR_OPENER = "GARAGE_DOOR_OPENER"

__all__ = [
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_TIMEOUT",
    "DEFAULT_SCAN_TIMEOUT",
    "LD2410AccountConnectionError",
    "LD2410ApiError",
    "LD2410AuthenticationError",
    "LD2410Model",
]
