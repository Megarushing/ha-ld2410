import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import UnitOfTime

from custom_components.ld2410.number import AbsenceDelayNumber


class FakeCoordinator:
    def __init__(self, device):
        self.device = device
        self.base_unique_id = "uid"
        self.device_name = "name"
        self.model = "ld2410"
        self.ble_device = SimpleNamespace(address="AA:BB")


@pytest.mark.asyncio
async def test_absence_delay_number_sets_value():
    device = SimpleNamespace(
        cmd_set_absence_delay=AsyncMock(), parsed_data={"absence_delay": 5}
    )
    coordinator = FakeCoordinator(device)
    number = AbsenceDelayNumber(coordinator)
    assert number.device_class == NumberDeviceClass.DURATION
    assert number.native_unit_of_measurement == UnitOfTime.SECONDS
    assert number.native_value == 5
    await number.async_set_native_value(10)
    device.cmd_set_absence_delay.assert_awaited_once_with(10)
