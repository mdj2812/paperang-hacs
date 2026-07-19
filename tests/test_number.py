"""Tests for paperang number platform — HA core style."""

import pytest
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.const import PERCENTAGE
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import DOMAIN

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def _setup_coordinator(hass: HomeAssistant, entry: MockConfigEntry):
    """Set up a config entry with a mock coordinator."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"available": True}
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator


class TestNumbers:
    async def test_all_numbers_created(self, hass: HomeAssistant) -> None:
        """All 4 number entities are created."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.number import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        add_entities.assert_called_once()
        entities = add_entities.call_args[0][0]
        assert len(entities) == 4

        for e in entities:
            assert e.unique_id.startswith(f"paperang_{entry.entry_id}_num_")

    async def test_font_size_defaults(self, hass: HomeAssistant) -> None:
        """Font size defaults to 24."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.number import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        entities = add_entities.call_args[0][0]
        font = next(e for e in entities if e._key == "font_size")
        assert font.native_value == 24
        assert font.native_min_value == 12
        assert font.native_max_value == 96

        # Verify value can be set (mock write to bypass entity registry)
        font.async_write_ha_state = MagicMock()
        await font.async_set_native_value(48)
        assert font.native_value == 48

    async def test_heat_density_defaults(self, hass: HomeAssistant) -> None:
        """Heat density defaults to 75%."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.number import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        entities = add_entities.call_args[0][0]
        heat = next(e for e in entities if e._key == "heat_density")
        assert heat.native_value == 75
        assert heat.native_unit_of_measurement == PERCENTAGE

        heat.async_write_ha_state = MagicMock()
        await heat.async_set_native_value(50)
        assert heat.native_value == 50
