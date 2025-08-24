"""Parse manufacturer firmware data for the device."""

from __future__ import annotations

from datetime import UTC, datetime


def _bcd_decode(byte: int) -> int:
    """Decode a BCD encoded byte to an integer."""
    return (byte >> 4) * 10 + (byte & 0x0F)


def _bcd_str(byte: int) -> str:
    """Return a zero padded string from a BCD encoded byte."""
    return f"{byte >> 4}{byte & 0x0F}"


def parse_firmware_data(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int | str | datetime]:
    """Return firmware details extracted from manufacturer data."""
    if not mfr_data or len(mfr_data) < 13:
        return {}

    minor = _bcd_str(mfr_data[0])
    major = mfr_data[1]
    hour = _bcd_decode(mfr_data[2])
    day = _bcd_decode(mfr_data[3])
    month = _bcd_decode(mfr_data[4])
    year_short = _bcd_decode(mfr_data[5])
    minute = _bcd_decode(mfr_data[6])

    firmware_version = f"{major}.{minor}.{year_short:02d}{month:02d}{day:02d}{hour:02d}"
    firmware_build_date = datetime(
        2000 + year_short, month, day, hour, minute, tzinfo=UTC
    )

    return {
        "firmware_version": firmware_version,
        "firmware_build_date": firmware_build_date,
    }
