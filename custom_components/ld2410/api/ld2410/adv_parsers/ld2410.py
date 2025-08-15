"""LD2410 parser."""

from __future__ import annotations

def process_ld2410(
    data: bytes | None, mfr_data: bytes | None
) -> dict[str, bool | int]:
    """Process woContact Sensor services data."""
    if data is None and mfr_data is None:
        return {}

    return {
        #TODO: Fill in advertisement data
    }
