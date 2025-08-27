"""Device constants library."""

# Obtained from the protocol documentation in https://h.hlktech.com/download/HLK-LD2410C-24G/1/LD2410C%20%E4%B8%B2%E5%8F%A3%E9%80%9A%E4%BF%A1%E5%8D%8F%E8%AE%AE%20V1.09.pdf

from __future__ import annotations

from ..enum import StrEnum

DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_TIMEOUT = 1
DEFAULT_SCAN_TIMEOUT = 5

CHARACTERISTIC_NOTIFY = "0000fff1-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_WRITE = "0000fff2-0000-1000-8000-00805f9b34fb"

# ---------- Frame constants (hex strings) ----------
TX_HEADER = "FDFCFBFA"  # Downlink (host→radar) command frame header. Command/ACK use same header/footer.
TX_FOOTER = "04030201"  # Downlink frame footer. ACK frames use this too.  status(2): "0000"=success, "0100"=failure. 
RX_HEADER = "F4F3F2F1"  # Uplink (radar→host) data frame header. Types: "01"=engineering, "02"=basic. 
RX_FOOTER = "F8F7F6F5"  # Uplink data frame footer.

# NOTE on ACKs: ACK intra-frame data begins with (sent_cmd | 0x0100) then the return payload.
# Example: send "FE00" → ACK contains "FE01" then status(2). 

# ---------- Command words (hex strings, little-endian) ----------

# Enable configuration session (must precede other config commands). Returns status + protocol version + buffer size.
CMD_ENABLE_CFG = "FF00"  # value: "0001"
# return: status(2) + proto_ver(2="0001") + buf_size(2="4000"). "0000"=OK, "0100"=fail. 

# End configuration session (resume normal working mode).
CMD_END_CFG = "FE00"  # value: (none)
# return: status(2). Send again CMD_ENABLE_CFG to re-enter config mode. 

# Set max detection gates (move & still) and "no-one" duration (unoccupied delay).
CMD_SET_MAX_GATES_AND_NOBODY = "6000"
# value (all words little-endian, values are u32 LE):
#   "0000"+<u32 move_gate 2..8>  +  "0100"+<u32 still_gate 2..8>  +  "0200"+<u32 nobody_sec 0..65535>
# return: status(2). Takes effect immediately; retained across power-cycles. Defaults in Table 7. 

# Read current configuration (gates, per-gate sensitivities, unoccupied duration).
CMD_READ_PARAMS = "6100"  # value: (none)
# return: status(2) + "AA"(1B) + N_max(1B) + cfg_max_move(1B) + cfg_max_still(1B)
#       + move_sens[0..N](1B each) + still_sens[0..N](1B each) + nobody_duration(2). 

# Enable engineering mode (uplink adds per-gate energy arrays, data type "01").
CMD_ENABLE_ENGINEERING = "6200"  # value: (none)
# return: status(2). Setting is volatile (lost on power-off). 

# Disable engineering mode (uplink reverts to basic target info, data type "02").
CMD_DISABLE_ENGINEERING = "6300"  # value: (none)
# return: status(2). 

# Set sensitivities for a specific gate or all gates.
CMD_SET_SENSITIVITY = "6400"
# value:
#   "0000"+<u32 gate_id 0..8 or 0x0000FFFF for ALL> + "0100"+<u32 move 0..100> + "0200"+<u32 still 0..100>
# return: status(2). Use ALL ("FFFF") to apply uniform values to every gate. 

# Read firmware version (type, major, minor/build).
CMD_READ_FW = "A000"  # value: (none)
# return: status(2) + fw_type(2="0001") + major(2) + minor(4). Example decodes to Vx.y.yyyymmddhh. 

# Set UART baud rate (persists; takes effect after reboot).
CMD_SET_BAUD = "A100"  # value: BAUD_* index(2)
# return: status(2). Indices: "0001"=9600 … "0008"=460800; factory default "0007"=256000. 

# Restore factory defaults (persists; takes effect after reboot).
CMD_FACTORY_RESET = "A200"  # value: (none)
# return: status(2). Table 7 lists default gates/sensitivities/baud. 

# Reboot module (module restarts after ACK).
CMD_REBOOT = "A300"  # value: (none)
# return: status(2). 

# Bluetooth on/off (requires reboot to apply).
CMD_BT_ONOFF = "A400"  # value: "0001"=ON, "0000"=OFF
# return: status(2). BT is ON by default. 

# Get MAC address (over UART).
CMD_GET_MAC = "A500"  # value: "0001"
# return: status(2) + fixed_type(1B="00") + MAC(6B; shown big-endian in example). 

# Obtain Bluetooth permission (checks password) — reply is sent via Bluetooth, not UART.
CMD_BT_GET_PERMISSION = (
    "A800"  # value: 6B password ("4869 4C69 6E6B" for "HiLink" split in LE pairs)
)
# return: status(2). Treat "0000"=allowed, "0100"=denied (per generic success/fail). 

# Set Bluetooth password (stores new 6B password).
CMD_BT_SET_PWD = "A900"  # value: 6B password (small-end order)
# return: status(2). 

# Set distance resolution per gate (0.75 m or 0.2 m; persists; needs reboot).
CMD_SET_RES = "AA00"  # value: RES_* index(2)
# return: status(2). "0000"→0.75 m; "0001"→0.20 m. Example shows index "0001". 

# Query distance resolution (returns current index).
CMD_GET_RES = "AB00"  # value: (none)
# return: status(2) + RES_* index(2). Example ACK shows "... 0001 00" → 0.2 m per gate. 

# Set auxiliary control (ambient light sensor & output config).
CMD_SET_AUX = "AD00"  # value: 4B config = [mode(1B) + threshold(1B) + out_level(1B) + reserved(1B)]
# return: status(2). Modes: 0x00=disable light sensor control (OUT always triggered by presence),
#        0x01=enable (OUT active only if ambient light < threshold), 0x02=enable (OUT active only if ambient light > threshold).
#        Out_level: 0x00=OUT default low (active high on detect), 0x01=OUT default high (active low on detect). 

# Read auxiliary control configuration.
CMD_GET_AUX = "AE00"  # value: (none)
# return: status(2) + 4B config (same format as CMD_SET_AUX). 

# Start automatic threshold detection (background noise calibration).
CMD_START_AUTO_THRESH = "0B00"  # value: <u16 duration_sec> (detection time in seconds)
# return: status(2). Sensor performs background noise detection for the given duration, then auto-adjusts sensitivities. 

# Query status of automatic threshold detection.
CMD_QUERY_AUTO_THRESH = "1B00"  # value: (none)
# return: status(2) + status_code(2). 0x0000 = not in progress, 0x0001 = in progress, 0x0002 = completed (calibration done). 

# ---------- Parameter words (for 0x0060 “max gates & nobody”) ----------
PAR_MAX_MOVE_GATE = "0000"  # u32 move gate: 2..8
PAR_MAX_STILL_GATE = "0100"  # u32 still gate: 2..8
PAR_NOBODY_DURATION = "0200"  # u32 seconds: 0..65535  (aka "no-one duration"). 

# ---------- Parameter words (for 0x0064 “set sensitivity”) ----------
PAR_DISTANCE_GATE = "0000"  # u32 gate: 0..8, or ALL_GATES
PAR_MOVE_SENS = "0100"  # u32 sensitivity: 0..100
PAR_STILL_SENS = "0200"  # u32 sensitivity: 0..100
ALL_GATES = "FFFF"  # special selector meaning "apply to all gates". 

# ---------- Baud rate indices (for CMD_SET_BAUD A100) ----------
BAUD_9600 = "0001"
BAUD_19200 = "0002"
BAUD_38400 = "0003"
BAUD_57600 = "0004"
BAUD_115200 = "0005"
BAUD_230400 = "0006"
BAUD_256000 = "0007"  # factory default
BAUD_460800 = "0008"  # per Table 6. 

# ---------- Distance resolution indices (for CMD_SET_RES / CMD_GET_RES) ----------
RES_PER_GATE_0_75M = "0000"  # each distance gate = 0.75 m
RES_PER_GATE_0_2M = "0001"  # each distance gate = 0.20 m  (query example returns "0001"). 

# ---------- Auxiliary control function values (for CMD_SET_AUX / CMD_GET_AUX) ----------
LIGHT_CONTROL_OFF = "00"    # 0x00 = Disable light-sensing control (ambient light ignored)
LIGHT_CONTROL_ENABLE_UNDER = "01"  # 0x01 = Enable aux control (OUT active if ambient < threshold)
LIGHT_CONTROL_ENABLE_OVER = "02"   # 0x02 = Enable aux control (OUT active if ambient > threshold)
LIGHT_THRESHOLD_DEFAULT = "80"     # Default light threshold = 0x80 (128)
OUT_LEVEL_LOW = "00"    # 0x00 = OUT default low (outputs low when idle, high when target detected)
OUT_LEVEL_HIGH = "01"   # 0x01 = OUT default high (outputs high when idle, low when target detected)

# ---------- Uplink data types (for RX payload interpretation) ----------
UPLINK_TYPE_ENGINEERING = "01"  # per-gate energies appended to basic target info
UPLINK_TYPE_BASIC = "02"  # basic target info only (default). 

class Model(StrEnum):
    """Device models."""
    LD2410 = "HLK-LD2410"
    # Additional models (e.g., LD2410B, LD2410C) can be represented by the same commands

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
    "CMD_SET_AUX",
    "CMD_GET_AUX",
    "CMD_START_AUTO_THRESH",
    "CMD_QUERY_AUTO_THRESH",
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
    # auxiliary control function values
    "LIGHT_CONTROL_OFF",
    "LIGHT_CONTROL_ENABLE_UNDER",
    "LIGHT_CONTROL_ENABLE_OVER",
    "LIGHT_THRESHOLD_DEFAULT",
    "OUT_LEVEL_LOW",
    "OUT_LEVEL_HIGH",
    # uplink data types
    "UPLINK_TYPE_ENGINEERING",
    "UPLINK_TYPE_BASIC",
]
