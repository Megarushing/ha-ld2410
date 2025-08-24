"""Test advertisement parser for LD2410."""

from datetime import datetime, timezone

from custom_components.ld2410.api import parse_advertisement_data

from . import LD2410b_SERVICE_INFO


def test_parse_firmware() -> None:
    """Test firmware version and build date are parsed."""
    adv = parse_advertisement_data(
        LD2410b_SERVICE_INFO.device, LD2410b_SERVICE_INFO.advertisement
    )
    assert adv is not None
    data = adv.data["data"]
    assert data["firmware_version"] == "2.44.24073110"
    assert data["firmware_build_date"] == datetime(
        2024, 7, 31, 10, 0, tzinfo=timezone.utc
    )
