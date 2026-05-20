"""Paperang P2 Printer - Select platform.

Provides dropdown selectors for print mode and image profile.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .const import DOMAIN
from .entity import PaperangEntity, make_device_info

PRINT_MODES = ["text", "image", "qr", "pickup_code"]
IMAGE_PROFILES = ["portrait", "landscape", "document", "high_contrast", "light"]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up select platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_info = make_device_info(entry)

    async_add_entities(
        [
            PaperangPrintModeSelect(coordinator, entry.entry_id, device_info),
            PaperangImageProfileSelect(coordinator, entry.entry_id, device_info),
        ]
    )


class PaperangPrintModeSelect(PaperangEntity, SelectEntity):
    """Select the print mode."""

    _attr_options = PRINT_MODES

    def __init__(self, coordinator, entry_id, device_info) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            entry_id,
            "Print Mode",
            "print_mode",
            "mdi:file-document-multiple-outline",
            device_info=device_info,
        )
        self._attr_current_option = "text"

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        self._attr_current_option = option
        self.async_write_ha_state()


class PaperangImageProfileSelect(PaperangEntity, SelectEntity):
    """Select the image print profile."""

    _attr_options = IMAGE_PROFILES

    def __init__(self, coordinator, entry_id, device_info) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            entry_id,
            "Image Profile",
            "image_profile",
            "mdi:image-edit-outline",
            device_info=device_info,
        )
        self._attr_current_option = "document"

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        self._attr_current_option = option
        self.async_write_ha_state()
