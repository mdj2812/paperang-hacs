"""Tests for paperang select platform — HA core style."""

import pytest
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
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


class TestSelects:
    async def test_both_selects_created(self, hass: HomeAssistant) -> None:
        """Both select entities are created."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.select import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        add_entities.assert_called_once()
        entities = add_entities.call_args[0][0]
        assert len(entities) == 2

        for e in entities:
            assert e.unique_id.startswith(f"paperang_{entry.entry_id}_")

    async def test_print_mode_default_and_options(self, hass: HomeAssistant) -> None:
        """Print mode defaults to 'text' with 4 options."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.select import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        entities = add_entities.call_args[0][0]
        mode = next(e for e in entities if e.unique_id.endswith("_print_mode"))
        assert mode.current_option == "text"
        assert mode.options == ["text", "image", "qr", "pickup_code"]

        mode.async_write_ha_state = MagicMock()
        await mode.async_select_option("qr")
        assert mode.current_option == "qr"

    async def test_image_profile_default_and_options(self, hass: HomeAssistant) -> None:
        """Image profile defaults to 'document' with 5 options."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.select import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        entities = add_entities.call_args[0][0]
        profile = next(e for e in entities if e.unique_id.endswith("_image_profile"))
        assert profile.current_option == "document"
        assert len(profile.options) == 5

        profile.async_write_ha_state = MagicMock()
        await profile.async_select_option("high_contrast")
        assert profile.current_option == "high_contrast"
