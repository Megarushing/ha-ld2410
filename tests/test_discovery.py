"""Tests for device discovery helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from custom_components.ld2410.api.discovery import GetDevices
from custom_components.ld2410.api.models import Advertisement


@pytest.mark.asyncio
async def test_detection_callback_stores_discovery() -> None:
    """Detection callback stores parsed advertisement data."""
    gd = GetDevices()
    device = BLEDevice(address="AA:BB", name="test", details=None)
    adv_data = AdvertisementData(
        local_name="test",
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        tx_power=None,
        rssi=-60,
        platform_data=(),
    )
    advert = Advertisement("AA:BB", {"model": "ld2410"}, device, -60)
    with patch(
        "custom_components.ld2410.api.discovery.parse_advertisement_data",
        return_value=advert,
    ):
        gd.detection_callback(device, adv_data)
    assert gd._adv_data == {"AA:BB": advert}


@pytest.mark.asyncio
async def test_discover_uses_bleak_scanner() -> None:
    """Discover calls start and stop on the bleak scanner."""
    gd = GetDevices()
    advert = Advertisement(
        "AA:BB",
        {"model": "ld2410"},
        BLEDevice(address="AA:BB", name="dev", details=None),
        -40,
    )
    gd._adv_data = {advert.address: advert}

    scanner = AsyncMock()
    with (
        patch(
            "custom_components.ld2410.api.discovery.bleak.BleakScanner",
            return_value=scanner,
        ),
        patch("asyncio.sleep", new=AsyncMock()),
    ):
        result = await gd.discover(scan_timeout=0)

    assert result == {advert.address: advert}
    assert scanner.start.call_count == 1
    assert scanner.stop.call_count == 1


@pytest.mark.asyncio
async def test_get_devices_by_model_triggers_discover() -> None:
    """_get_devices_by_model calls discover when cache empty."""
    gd = GetDevices()
    advert = Advertisement(
        "AA:BB",
        {"model": "ld2410"},
        BLEDevice(address="AA:BB", name="dev", details=None),
        -40,
    )

    async def fake_discover(*args, **kwargs):
        gd._adv_data = {advert.address: advert}
        return gd._adv_data

    with patch.object(gd, "discover", side_effect=fake_discover) as mock_disc:
        result = await gd._get_devices_by_model("ld2410")
    assert result == {advert.address: advert}
    mock_disc.assert_called_once()


@pytest.mark.asyncio
async def test_get_device_data_triggers_discover() -> None:
    """get_device_data calls discover when cache empty."""
    gd = GetDevices()
    advert = Advertisement(
        "AA:BB",
        {"address": "AA:BB"},
        BLEDevice(address="AA:BB", name="dev", details=None),
        -40,
    )

    async def fake_discover(*args, **kwargs):
        gd._adv_data = {advert.address: advert}
        return gd._adv_data

    with patch.object(gd, "discover", side_effect=fake_discover) as mock_disc:
        result = await gd.get_device_data("AA:BB")
    assert result == {advert.address: advert}
    mock_disc.assert_called_once()
