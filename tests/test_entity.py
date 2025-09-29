"""Tests for the base entity helpers."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ld2410.number import LightSensitivityNumber


@pytest.fixture
def coordinator() -> SimpleNamespace:
    """Return a minimal coordinator stub for testing."""

    device = SimpleNamespace(
        parsed_data={"light_threshold": 10},
        is_reconnecting=False,
        is_connected=True,
        subscribe=MagicMock(return_value=lambda: None),
        update=AsyncMock(),
    )

    return SimpleNamespace(
        device=device,
        ble_device=SimpleNamespace(address="AA:BB:CC:DD:EE:FF"),
        base_unique_id="test-device",
        model=SimpleNamespace(name="LD2410"),
        device_name="Test device",
        last_update_success=True,
    )


@dataclass(slots=True)
class _DummyPlatform:
    """Minimal platform stub for entities."""

    platform_name: str = "number"
    domain: str = "number"
    default_language_platform_translations: dict[str, str] | None = None
    component_translations: dict[str, str] | None = None
    platform_translations: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.default_language_platform_translations is None:
            self.default_language_platform_translations = {}
        if self.component_translations is None:
            self.component_translations = {}
        if self.platform_translations is None:
            self.platform_translations = {}


@pytest.fixture
def entity(hass: HomeAssistant, coordinator: SimpleNamespace) -> LightSensitivityNumber:
    """Return a configured entity instance."""

    entity = LightSensitivityNumber(coordinator)
    entity.hass = hass
    entity.entity_id = "number.test_ld2410"
    entity.platform = _DummyPlatform()
    entity.registry_entry = None
    return entity


async def test_handle_update_skips_disabled_entity(
    hass: HomeAssistant, coordinator: SimpleNamespace
) -> None:
    """Disabled entities should not trigger state writes."""

    test_entity = LightSensitivityNumber(coordinator)
    test_entity.hass = hass
    test_entity.entity_id = "number.test_disabled"
    test_entity.platform = _DummyPlatform()
    test_entity.registry_entry = SimpleNamespace(disabled=True, disabled_by="user")

    with patch.object(test_entity, "async_write_ha_state") as mock_write:
        test_entity._handle_coordinator_update()

    mock_write.assert_not_called()


async def test_handle_update_skips_when_state_unchanged(
    hass: HomeAssistant, entity: LightSensitivityNumber
) -> None:
    """Repeated updates with the same data should be ignored."""

    entity._handle_coordinator_update()
    await hass.async_block_till_done()

    with patch.object(entity, "async_write_ha_state") as mock_write:
        entity._handle_coordinator_update()
        await hass.async_block_till_done()

    mock_write.assert_not_called()


async def test_handle_update_writes_state_on_change(
    hass: HomeAssistant, entity: LightSensitivityNumber, coordinator: SimpleNamespace
) -> None:
    """State changes should be forwarded to Home Assistant."""

    entity._handle_coordinator_update()
    await hass.async_block_till_done()

    coordinator.device.parsed_data = {"light_threshold": 42}

    with patch.object(entity, "async_write_ha_state") as mock_write:
        entity._handle_coordinator_update()
        await hass.async_block_till_done()

    mock_write.assert_called_once()
