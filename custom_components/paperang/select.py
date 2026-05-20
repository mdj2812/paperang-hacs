# pylint: disable=import-error,duplicate-code
"""Paperang P2 Printer - Select platform.

Provides dropdown selectors for print mode and image profile.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

PRINT_MODES = ["text", "image", "qr", "pickup_code"]
IMAGE_PROFILES = ["portrait", "landscape", "document", "high_contrast", "light"]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up select platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = f"paperang_{entry.entry_id}"
    device_info = DeviceInfo(
        identifiers={("paperang", device_id)},
    )

    async_add_entities([
        PaperangPrintModeSelect(coordinator, device_info, device_id),
        PaperangImageProfileSelect(coordinator, device_info, device_id),
    ])


class PaperangPrintModeSelect(CoordinatorEntity, SelectEntity):
    """Select the print mode."""

    _attr_has_entity_name = True
    _attr_options = PRINT_MODES

    def __init__(self, coordinator, device_info, device_id) -> None:
        """Initialize."""
        self._attr_name = "Print Mode"
        self._attr_unique_id = f"{device_id}_print_mode"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:file-document-multiple-outline"
        self._attr_current_option = "text"
        super().__init__(coordinator)

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class PaperangImageProfileSelect(CoordinatorEntity, SelectEntity):
    """Select the image print profile."""

    _attr_has_entity_name = True
    _attr_options = IMAGE_PROFILES

    def __init__(self, coordinator, device_info, device_id) -> None:
        """Initialize."""
        self._attr_name = "Image Profile"
        self._attr_unique_id = f"{device_id}_image_profile"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:image-edit-outline"
        self._attr_current_option = "document"
        super().__init__(coordinator)

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
