"""Test baud rate select."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.ld2410.select import BaudRateSelect


class FakeCoordinator:
    def __init__(self, device):
        self.device = device
        self.base_unique_id = "uid"
        self.device_name = "name"
        self.model = "ld2410"
        self.ble_device = SimpleNamespace(address="AA:BB")


@pytest.mark.asyncio
async def test_baud_rate_select_sets_option():
    device = SimpleNamespace(
        cmd_set_baud_rate=AsyncMock(), parsed_data={"baud_rate": 256000}
    )
    coordinator = FakeCoordinator(device)
    select = BaudRateSelect(coordinator)
    assert select.current_option == "256000"
    assert "115200" in select.options
    await select.async_select_option("115200")
    device.cmd_set_baud_rate.assert_awaited_once_with(115200)
