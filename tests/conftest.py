"""Define fixtures available for all tests."""

import pytest

from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant

# Try to import from the tests directory first, fall back to our own implementation
try:
    from tests.common import MockConfigEntry
except ImportError:
    from homeassistant.config_entries import ConfigEntry
    from typing import Any
    
    class MockConfigEntry(ConfigEntry):
        """Mock config entry for testing."""
        
        def __init__(
            self,
            *,
            domain: str,
            data: dict[str, Any] | None = None,
            options: dict[str, Any] | None = None,
            entry_id: str | None = None,
            source: str = "user",
            title: str = "Mock Title",
            unique_id: str | None = None,
            version: int = 1,
            minor_version: int = 1,
        ) -> None:
            """Initialize a mock config entry."""
            kwargs = {
                "version": version,
                "minor_version": minor_version,
                "domain": domain,
                "title": title,
                "data": data or {},
                "options": options or {},
                "source": source,
                "entry_id": entry_id or "mock_entry_id",
                "unique_id": unique_id,
            }
            super().__init__(**kwargs)


from custom_components.ld2410.const import DOMAIN

@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth: None) -> None:
    """Auto mock bluetooth."""


@pytest.fixture
def mock_entry_factory():
    """Fixture to create a MockConfigEntry for the LD2410 integration."""
    return lambda: MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
            CONF_NAME: "LD2410 Test",
        },
        unique_id="aabbccddeeff",
    )


@pytest.fixture
async def hass_with_ld2410(hass: HomeAssistant, mock_entry_factory) -> HomeAssistant:
    """Set up the LD2410 integration in Home Assistant."""
    entry = mock_entry_factory()
    entry.add_to_hass(hass)
    return hass
