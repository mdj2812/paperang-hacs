# pylint: disable=import-error
"""Paperang P2 Printer - Text platform.

Provides a text input entity for print content.
"""

from __future__ import annotations

from homeassistant.components.text import TextEntity

from .const import DOMAIN
from .entity import PaperangEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up text platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            PaperangPrintContent(coordinator),
        ]
    )


class PaperangPrintContent(PaperangEntity, TextEntity):
    """Text input for print content (text, URL, or QR data)."""

    _attr_mode = "text"

    def __init__(self, coordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            "Print Content",
            "paperang_p2_print_content",
            "mdi:form-textbox",
        )
        self._attr_native_value = ""

    async def async_set_value(self, value: str) -> None:
        """Set text value."""
        self._attr_native_value = value
        self.async_write_ha_state()
