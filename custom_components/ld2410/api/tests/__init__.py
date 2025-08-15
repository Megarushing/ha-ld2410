from dataclasses import dataclass

from ..ld2410 import LD2410Model


@dataclass
class AdvTestCase:
    manufacturer_data: bytes | None
    service_data: bytes | None
    data: dict
    model: str | bytes
    modelFriendlyName: str
    modelName: LD2410Model
