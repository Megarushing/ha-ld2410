"""Advertisement parser."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypedDict

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .adv_parsers.firmware_parser import parse_firmware_data
from .const import Model
from .models import Advertisement

_LOGGER = logging.getLogger(__name__)

SERVICE_DATA_ORDER = ("0000af30-0000-1000-8000-00805f9b34fb",)
MFR_DATA_ORDER = (256, 1494)


class SupportedType(TypedDict):
    """Supported device type."""

    modelName: Model
    modelFriendlyName: str
    func: Callable[[bytes, bytes | None], dict[str, bool | int]]
    manufacturer_id: int | None
    manufacturer_data_length: int | None


SUPPORTED_TYPES: dict[str | bytes, SupportedType] = {
    "t": {
        "modelName": Model.LD2410,
        "modelFriendlyName": "HLK-LD2410",
        "func": parse_firmware_data,
        "manufacturer_id": 256,
    },
}


def parse_advertisement_data(
    device: BLEDevice,
    advertisement_data: AdvertisementData,
    _model: Model | None = None,
) -> Advertisement | None:
    """Parse advertisement data."""
    service_data = advertisement_data.service_data

    _service_data = None
    for uuid in SERVICE_DATA_ORDER:
        if uuid in service_data:
            _service_data = service_data[uuid]
            break

    _mfr_data = None
    for mfr_id in MFR_DATA_ORDER:
        if mfr_id in advertisement_data.manufacturer_data:
            _mfr_data = advertisement_data.manufacturer_data[mfr_id]
            break

    if _mfr_data is None and _service_data is None:
        return None

    try:
        data = _parse_data(
            _service_data,
            _mfr_data,
        )
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Failed to parse advertisement data: %s", advertisement_data)
        return None

    if not data:
        return None

    return Advertisement(
        device.address, data, device, advertisement_data.rssi, bool(_service_data)
    )


@lru_cache(maxsize=128)
def _parse_data(
    _service_data: bytes | None,
    _mfr_data: bytes | None,
) -> dict[str, Any] | None:
    """Parse advertisement data."""
    type_data = SUPPORTED_TYPES["t"]

    return {
        "modelFriendlyName": type_data["modelFriendlyName"],
        "modelName": type_data["modelName"],
        "data": type_data["func"](_service_data, _mfr_data),
    }
