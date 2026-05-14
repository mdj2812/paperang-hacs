# pylint: disable=import-error
"""Paperang P2 Printer - Select platform.

Provides dropdown selectors for print mode and image profile.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import DOMAIN
from .entity import PaperangEntity

PRINT_MODES = ["text", "image", "qr", "pickup_code"]
IMAGE_PROFILES = ["portrait", "landscape", "document", "high_contrast", "light"]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up select platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        PaperangPrintModeSelect(coordinator),
        PaperangImageProfileSelect(coordinator),
    ])


class PaperangPrintModeSelect(PaperangEntity, SelectEntity):
    """Select the print mode."""

    _attr_options = PRINT_MODES

    def __init__(self, coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "Print Mode", "paperang_p2_print_mode",
                         "mdi:file-document-multiple-outline")
        self._attr_current_option = "text"

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        self._attr_current_option = option
        self.async_write_ha_state()


class PaperangImageProfileSelect(PaperangEntity, SelectEntity):
    """Select the image print profile."""

    _attr_options = IMAGE_PROFILES

    def __init__(self, coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "Image Profile", "paperang_p2_image_profile",
                         "mdi:image-edit-outline")
        self._attr_current_option = "document"

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        self._attr_current_option = option
        self.async_write_ha_state()
