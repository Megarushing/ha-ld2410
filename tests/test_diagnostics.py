"""Tests for the diagnostics data provided by the LD2410 integration."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from custom_components.ld2410.const import (
    CONF_RETRY_COUNT,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
)
from collections.abc import Callable, Coroutine
from aiohttp.test_utils import TestClient
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ADDRESS, CONF_NAME, CONF_SENSOR_TYPE
from homeassistant.core import HomeAssistant
from typing import Any

from . import LD2410b_SERVICE_INFO

try:
    from tests.common import MockConfigEntry
except ImportError:
    from .mocks import MockConfigEntry

try:
    from tests.components.bluetooth import inject_bluetooth_service_info
except ImportError:
    from .mocks import inject_bluetooth_service_info

try:
    from tests.components.diagnostics import get_diagnostics_for_config_entry
except ImportError:
    from .mocks import get_diagnostics_for_config_entry


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: Callable[..., Coroutine[Any, Any, TestClient]],
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics for config entry."""

    inject_bluetooth_service_info(hass, LD2410b_SERVICE_INFO)

    with patch(
        "custom_components.ld2410.api.LD2410.update",
        return_value=None,
    ):
        mock_config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "test-name",
                CONF_SENSOR_TYPE: "ld2410",
            },
            unique_id="aabbccddeeff",
            options={CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT},
            subentries_data=(
                {
                    "title": "Subentry",
                    "data": {},
                    "subentry_type": "test",
                },
            ),
        )
        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_config_entry.state is ConfigEntryState.LOADED

    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )
    assert result == snapshot(
        exclude=props("created_at", "modified_at", "entry_id", "time", "subentry_id")
    )
