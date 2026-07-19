"""Tests for paperang text platform — HA core style."""

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


class TestText:
    async def test_print_content_created(self, hass: HomeAssistant) -> None:
        """Print content text entity is created."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.text import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        entities = add_entities.call_args[0][0]
        assert len(entities) == 1
        e = entities[0]
        assert e.unique_id == f"paperang_{entry.entry_id}_print_content"
        assert e.translation_key == "print_content"
        assert e.native_value == ""

    async def test_set_value(self, hass: HomeAssistant) -> None:
        """Setting a value updates the native value."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.text import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        e = add_entities.call_args[0][0][0]
        e.async_write_ha_state = MagicMock()
        await e.async_set_value("Hello World")
        assert e.native_value == "Hello World"
