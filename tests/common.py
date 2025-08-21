"""Local test utilities overriding upstream.

Provides MockConfigEntry and BLE helpers for tests.
"""

from .mocks import MockConfigEntry, generate_advertisement_data, generate_ble_device

__all__ = [
    "MockConfigEntry",
    "generate_advertisement_data",
    "generate_ble_device",
]
