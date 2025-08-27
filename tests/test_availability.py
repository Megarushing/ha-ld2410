import pytest
from unittest.mock import AsyncMock, PropertyMock, patch

from custom_components.ld2410.const import DOMAIN
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSOR_TYPE,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.ld2410.api.devices.device import Device
from custom_components.ld2410.api.const import RX_HEADER, RX_FOOTER

from . import LD2410b_SERVICE_INFO

try:
    from tests.common import MockConfigEntry
except ImportError:  # pragma: no cover - testing fallback
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import inject_bluetooth_service_info
except ImportError:  # pragma: no cover - testing fallback
    from .mocks import inject_bluetooth_service_info


@pytest.mark.asyncio
async def test_entities_stay_available_with_uplink_frames(hass: HomeAssistant) -> None:
    """Entities stay available when uplink frames are received without advertisements."""
    await async_setup_component(hass, DOMAIN, {})
    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "test-password",
            CONF_SENSOR_TYPE: "ld2410",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_hass(hass)

    with (
        patch("custom_components.ld2410.api.close_stale_connections_by_address"),
        patch(
            "custom_components.ld2410.api.LD2410.cmd_send_bluetooth_password",
            AsyncMock(),
        ),
        patch(
            "custom_components.ld2410.api.LD2410.connect_and_update",
            AsyncMock(),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = entry.runtime_data
    entity_id = "binary_sensor.test_name_motion"
    assert hass.states.get(entity_id).state != STATE_UNAVAILABLE
    assert not coordinator._was_unavailable

    payload_hex = (
        "01aa034e00334e00643e000808123318050403050306000064202627190f1501015500"
    )
    payload = bytes.fromhex(payload_hex)
    length = len(payload).to_bytes(2, "little").hex()
    frame_hex = RX_HEADER + length + payload_hex + RX_FOOTER

    with patch.object(
        Device, "is_connected", new_callable=PropertyMock, return_value=True
    ):
        coordinator.device._notification_handler(0, bytearray.fromhex(frame_hex))
        coordinator._async_handle_unavailable(LD2410b_SERVICE_INFO)
        await hass.async_block_till_done()

    assert hass.states.get(entity_id).state != STATE_UNAVAILABLE
    assert not coordinator._was_unavailable
