"""Device constants library."""

from __future__ import annotations

from ..enum import StrEnum

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

CHARACTERISTIC_NOTIFY = "0000fff1-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_WRITE = "0000fff2-0000-1000-8000-00805f9b34fb"

# ---------- Frame constants (hex strings) ----------
TX_HEADER = "FDFCFBFA"  # Downlink (host→radar) command frame header. Command/ACK use same header/footer.
TX_FOOTER = "04030201"  # Downlink frame footer. ACK frames use this too.  status(2): "0000"=success, "0100"=failure. :contentReference[oaicite:1]{index=1}
RX_HEADER = "F4F3F2F1"  # Uplink (radar→host) data frame header. Types: "01"=engineering, "02"=basic. :contentReference[oaicite:2]{index=2}
RX_FOOTER = "F8F7F6F5"  # Uplink data frame footer.

# NOTE on ACKs: ACK intra-frame data begins with (sent_cmd | 0x0100) then the return payload.
# Example: send "FE00" → ACK contains "FE01" then status(2). :contentReference[oaicite:3]{index=3}


# ---------- Command words (hex strings, little-endian) ----------

# Enable configuration session (must precede other config commands). Returns status + protocol version + buffer size.
CMD_ENABLE_CFG = "FF00"  # value: "0001"
# return: status(2) + proto_ver(2="0001") + buf_size(2="4000"). "0000"=OK, "0100"=fail. :contentReference[oaicite:4]{index=4}

# End configuration session (resume normal working mode).
CMD_END_CFG = "FE00"  # value: (none)
# return: status(2). Send again CMD_ENABLE_CFG to re-enter config mode. :contentReference[oaicite:5]{index=5}

# Set max detection gates (move & still) and "no-one" duration (unoccupied delay).
CMD_SET_MAX_GATES_AND_NOBODY = "6000"
# value (all words little-endian, values are u32 LE):
#   "0000"+<u32 move_gate 2..8>  +  "0100"+<u32 still_gate 2..8>  +  "0200"+<u32 nobody_sec 0..65535>
# return: status(2). Takes effect immediately; retained across power-cycles. Defaults in Table 7. :contentReference[oaicite:6]{index=6}

# Read current configuration (gates, per-gate sensitivities, unoccupied duration).
CMD_READ_PARAMS = "6100"  # value: (none)
# return: status(2) + "AA"(1B) + N_max(1B) + cfg_max_move(1B) + cfg_max_still(1B)
#       + move_sens[0..N](1B each) + still_sens[0..N](1B each) + nobody_duration(2). :contentReference[oaicite:7]{index=7}

# Enable engineering mode (uplink adds per-gate energy arrays, data type "01").
CMD_ENABLE_ENGINEERING = "6200"  # value: (none)
# return: status(2). Setting is volatile (lost on power-off). :contentReference[oaicite:8]{index=8}

# Disable engineering mode (uplink reverts to basic target info, data type "02").
CMD_DISABLE_ENGINEERING = "6300"  # value: (none)
# return: status(2). :contentReference[oaicite:9]{index=9}

# Set sensitivities for a specific gate or all gates.
CMD_SET_SENSITIVITY = "6400"
# value:
#   "0000"+<u32 gate_id 0..8 or 0x0000FFFF for ALL> + "0100"+<u32 move 0..100> + "0200"+<u32 still 0..100>
# return: status(2). Use ALL ("FFFF") to apply uniform values to every gate. :contentReference[oaicite:10]{index=10}

# Read firmware version (type, major, minor/build).
CMD_READ_FW = "A000"  # value: (none)
# return: status(2) + fw_type(2="0001") + major(2) + minor(4). Example decodes to Vx.y.yyyymmddhh. :contentReference[oaicite:11]{index=11}

# Set UART baud rate (persists; takes effect after reboot).
CMD_SET_BAUD = "A100"  # value: BAUD_* index(2)
# return: status(2). Indices: "0001"=9600 … "0008"=460800; factory default "0007"=256000. :contentReference[oaicite:12]{index=12}

# Restore factory defaults (persists; takes effect after reboot).
CMD_FACTORY_RESET = "A200"  # value: (none)
# return: status(2). Table 7 lists default gates/sensitivities/baud. :contentReference[oaicite:13]{index=13}

# Reboot module (module restarts after ACK).
CMD_REBOOT = "A300"  # value: (none)
# return: status(2). :contentReference[oaicite:14]{index=14}

# Bluetooth on/off (requires reboot to apply).
CMD_BT_ONOFF = "A400"  # value: "0001"=ON, "0000"=OFF
# return: status(2). BT is ON by default. :contentReference[oaicite:15]{index=15}

# Get MAC address (over UART).
CMD_GET_MAC = "A500"  # value: "0001"
# return: status(2) + fixed_type(1B="00") + MAC(6B; shown big-endian in example). :contentReference[oaicite:16]{index=16}

# Obtain Bluetooth permission (checks password) — reply is sent via Bluetooth, not UART.
CMD_BT_GET_PERMISSION = (
    "A800"  # value: 6B password ("4869 4C69 6E6B" for "HiLink" split in LE pairs)
)
# return: status(2). Treat "0000"=allowed, "0100"=denied (per generic success/fail). :contentReference[oaicite:17]{index=17}

# Set Bluetooth password (stores new 6B password).
CMD_BT_SET_PWD = "A900"  # value: 6B password (small-end order)
# return: status(2). :contentReference[oaicite:18]{index=18}

# Set distance resolution per gate (0.75 m or 0.2 m; persists; needs reboot).
CMD_SET_RES = "AA00"  # value: RES_* index(2)
# return: status(2). "0000"→0.75 m; "0001"→0.20 m. Example shows index "0001". :contentReference[oaicite:19]{index=19}

# Query distance resolution (returns current index).
CMD_GET_RES = "AB00"  # value: (none)
# return: status(2) + RES_* index(2). Example ACK shows "... 0001 00" → 0.2 m per gate. :contentReference[oaicite:20]{index=20}


# ---------- Parameter words (for 0x0060 “max gates & nobody”) ----------
PAR_MAX_MOVE_GATE = "0000"  # u32 move gate: 2..8
PAR_MAX_STILL_GATE = "0100"  # u32 still gate: 2..8
PAR_NOBODY_DURATION = "0200"  # u32 seconds: 0..65535  (aka "no-one duration"). :contentReference[oaicite:21]{index=21}

# ---------- Parameter words (for 0x0064 “set sensitivity”) ----------
PAR_DISTANCE_GATE = "0000"  # u32 gate: 0..8, or ALL_GATES
PAR_MOVE_SENS = "0100"  # u32 sensitivity: 0..100
PAR_STILL_SENS = "0200"  # u32 sensitivity: 0..100
ALL_GATES = "FFFF"  # special selector meaning "apply to all gates". :contentReference[oaicite:22]{index=22}

# ---------- Baud rate indices (for CMD_SET_BAUD A100) ----------
BAUD_9600 = "0001"
BAUD_19200 = "0002"
BAUD_38400 = "0003"
BAUD_57600 = "0004"
BAUD_115200 = "0005"
BAUD_230400 = "0006"
BAUD_256000 = "0007"  # factory default
BAUD_460800 = "0008"  # per Table 6. :contentReference[oaicite:23]{index=23}

# ---------- Distance resolution indices (for CMD_SET_RES / CMD_GET_RES) ----------
RES_PER_GATE_0_75M = "0000"  # each distance gate = 0.75 m
RES_PER_GATE_0_2M = "0001"  # each distance gate = 0.20 m  (query example returns "0001"). :contentReference[oaicite:24]{index=24}

# ---------- Uplink data types (for RX payload interpretation) ----------
UPLINK_TYPE_ENGINEERING = "01"  # per-gate energies appended to basic target info
UPLINK_TYPE_BASIC = (
    "02"  # basic target info only (default). :contentReference[oaicite:25]{index=25}
)


class Model(StrEnum):
    """Device models."""

    LD2410 = "HLK-LD2410"


__all__ = [
    # exports
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_RETRY_TIMEOUT",
    "DEFAULT_SCAN_TIMEOUT",
    "Model",
    "CHARACTERISTIC_NOTIFY",
    "CHARACTERISTIC_WRITE",
    # frame constants (hex strings)
    "TX_HEADER",
    "TX_FOOTER",
    "RX_HEADER",
    "RX_FOOTER",
    # command words (hex strings, little-endian)
    "CMD_ENABLE_CFG",
    "CMD_END_CFG",
    "CMD_SET_MAX_GATES_AND_NOBODY",
    "CMD_READ_PARAMS",
    "CMD_ENABLE_ENGINEERING",
    "CMD_DISABLE_ENGINEERING",
    "CMD_SET_SENSITIVITY",
    "CMD_READ_FW",
    "CMD_SET_BAUD",
    "CMD_FACTORY_RESET",
    "CMD_REBOOT",
    "CMD_BT_ONOFF",
    "CMD_GET_MAC",
    "CMD_BT_GET_PERMISSION",
    "CMD_BT_SET_PWD",
    "CMD_SET_RES",
    "CMD_GET_RES",
    # parameter words
    "PAR_MAX_MOVE_GATE",
    "PAR_MAX_STILL_GATE",
    "PAR_NOBODY_DURATION",
    "PAR_DISTANCE_GATE",
    "PAR_MOVE_SENS",
    "PAR_STILL_SENS",
    "ALL_GATES",
    # baud rate indices
    "BAUD_9600",
    "BAUD_19200",
    "BAUD_38400",
    "BAUD_57600",
    "BAUD_115200",
    "BAUD_230400",
    "BAUD_256000",
    "BAUD_460800",
    # distance resolution indices
    "RES_PER_GATE_0_75M",
    "RES_PER_GATE_0_2M",
    # uplink data types
    "UPLINK_TYPE_ENGINEERING",
    "UPLINK_TYPE_BASIC",
]


# OLD commands for reference
# CMD_BT_PASS_PRE = b"\xfd\xfc\xfb\xfa\x08\x00\xa8\x00"
# CMD_BT_PASS_DEFAULT = b"HiLink"
# CMD_BT_PASS_POST = b"\x04\x03\x02\x01"
# CMD_ENABLE_CONFIG = b"\xfd\xfc\xfb\xfa\x04\x00\xff\x00\x01\x00\x04\x03\x02\x01"
# CMD_ENABLE_ENGINEERING_MODE = b"\xfd\xfc\xfb\xfa\x02\x00b\x00\x04\x03\x02\x01"
# CMD_DISABLE_CONFIG = b"\xfd\xfc\xfb\xfa\x02\x00\xfe\x00\x04\x03\x02\x01"
#
# MOVING_TARGET = 1
# STATIC_TARGET = 2
#
# frame_start = b"\xf4\xf3\xf2\xf1"
# frame_length = b"(?P<length>..)"
# frame_engineering_mode = b"(?P<engineering>\x01|\x02)"
# frame_head = b"\xaa"
# frame_target_state = b"(?P<target_state>\x00|\x01|\x02|\x03)"
# frame_moving_target_distance = b"(?P<moving_target_distance>..)"
# frame_moving_target_energy = b"(?P<moving_target_energy>.)"
# frame_static_target_distance = b"(?P<static_target_distance>..)"
# frame_static_target_energy = b"(?P<static_target_energy>.)"
# frame_detection_distance = b"(?P<detection_distance>..)"
# frame_engineering_data = b"(?P<engineering_data>.+?)?"
# frame_tail = b"\x55"
# frame_check = b"\x00"
# frame_end = b"\xf8\xf7\xf6\xf5"
#
# frame_maximum_motion_gates = b"(?P<maximum_motion_gates>.)"
# frame_maximum_static_gates = b"(?P<maximum_static_gates>.)"
# frame_motion_energy_gates = b"(?P<motion_energy_gates>.{9})"
# frame_static_energy_gates = b"(?P<static_energy_gates>.{9})"
# frame_additional_information = b"(?P<additional_information>.*)"
#
# frame_regex = (
#         frame_start
#         + frame_length
#         + frame_engineering_mode
#         + frame_head
#         + frame_target_state
#         + frame_moving_target_distance
#         + frame_moving_target_energy
#         + frame_static_target_distance
#         + frame_static_target_energy
#         + frame_detection_distance
#         + frame_engineering_data
#         + frame_tail
#         + frame_check
#         + frame_end
# )
#
# engineering_frame_regex = (
#         frame_maximum_motion_gates
#         + frame_maximum_static_gates
#         + frame_motion_energy_gates
#         + frame_static_energy_gates
#         + frame_additional_information
# )
