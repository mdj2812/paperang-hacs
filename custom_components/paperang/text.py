"""Paperang P2 Printer - Text platform.

Provides a text input entity for print content.
"""

from __future__ import annotations

from homeassistant.components.text import TextEntity

from .const import DOMAIN
from .entity import PaperangEntity, make_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up text platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_info = make_device_info(entry)

    async_add_entities(
        [
            PaperangPrintContent(coordinator, entry.entry_id, device_info),
        ]
    )


class PaperangPrintContent(PaperangEntity, TextEntity):
    """Text input for print content (text, URL, or QR data)."""

    _attr_mode = "text"

    def __init__(self, coordinator, entry_id, device_info) -> None:
        """Initialize."""
        super().__init__(
            coordinator, entry_id, "Print Content", "print_content",
            "mdi:form-textbox", device_info=device_info,
        )
        self._attr_native_value = ""

    async def async_set_value(self, value: str) -> None:
        """Set text value."""
        self._attr_native_value = value
        self.async_write_ha_state()
