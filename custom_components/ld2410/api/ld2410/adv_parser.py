"""LD2410 advertisement parser."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypedDict

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .adv_parsers.contact import process_wocontact
from .adv_parsers.motion import process_wopresence
from .adv_parsers.ld2410 import process_ld2410
from .const import LD2410Model
from .models import LD2410Advertisement

_LOGGER = logging.getLogger(__name__)

SERVICE_DATA_ORDER = (
    "0000af30-0000-1000-8000-00805f9b34fb",
)
MFR_DATA_ORDER = (256, 1494)


class LD2410SupportedType(TypedDict):
    """Supported type of LD2410."""

    modelName: LD2410Model
    modelFriendlyName: str
    func: Callable[[bytes, bytes | None], dict[str, bool | int]]
    manufacturer_id: int | None
    manufacturer_data_length: int | None


SUPPORTED_TYPES: dict[str | bytes, LD2410SupportedType] = {
    "d": {
        "modelName": LD2410Model.CONTACT_SENSOR,
        "modelFriendlyName": "Contact Sensor",
        "func": process_wocontact,
        "manufacturer_id": 256,
    },
    "s": {
        "modelName": LD2410Model.MOTION_SENSOR,
        "modelFriendlyName": "Motion Sensor",
        "func": process_wopresence,
        "manufacturer_id": 256,
    },
    "t": {
        "modelName": LD2410Model.LD2410,
        "modelFriendlyName": "HLK-LD2410",
        "func": process_ld2410,
        "manufacturer_id": 256,
    },
}

_LD2410_MODEL_TO_CHAR = {
    model_data["modelName"]: model_chr
    for model_chr, model_data in SUPPORTED_TYPES.items()
}

MODELS_BY_MANUFACTURER_DATA: dict[int, list[tuple[str, LD2410SupportedType]]] = {
    mfr_id: [] for mfr_id in MFR_DATA_ORDER
}
for model_chr, model in SUPPORTED_TYPES.items():
    if "manufacturer_id" in model:
        mfr_id = model["manufacturer_id"]
        MODELS_BY_MANUFACTURER_DATA[mfr_id].append((model_chr, model))


def parse_advertisement_data(
    device: BLEDevice,
    advertisement_data: AdvertisementData,
    model: LD2410Model | None = None,
) -> LD2410Advertisement | None:
    """Parse advertisement data."""
    service_data = advertisement_data.service_data

    _service_data = None
    for uuid in SERVICE_DATA_ORDER:
        if uuid in service_data:
            _service_data = service_data[uuid]
            break

    _mfr_data = None
    _mfr_id = None
    for mfr_id in MFR_DATA_ORDER:
        if mfr_id in advertisement_data.manufacturer_data:
            _mfr_id = mfr_id
            _mfr_data = advertisement_data.manufacturer_data[mfr_id]
            break

    if _mfr_data is None and _service_data is None:
        return None

    try:
        data = _parse_data(
            _service_data,
            _mfr_data,
            _mfr_id,
            model,
        )
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Failed to parse advertisement data: %s", advertisement_data)
        return None

    if not data:
        return None

    return LD2410Advertisement(
        device.address, data, device, advertisement_data.rssi, bool(_service_data)
    )


@lru_cache(maxsize=128)
def _parse_data(
    _service_data: bytes | None,
    _mfr_data: bytes | None,
    _mfr_id: int | None = None,
    _ld2410_model: LD2410Model | None = None,
) -> dict[str, Any] | None:
    """Parse advertisement data."""
    type_data = SUPPORTED_TYPES.get("t")

    data = {
        "modelFriendlyName": type_data["modelFriendlyName"],
        "modelName": type_data["modelName"],
        "data": type_data["func"](_service_data, _mfr_data),
    }

    return data
