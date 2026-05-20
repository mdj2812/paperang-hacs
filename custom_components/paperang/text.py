# pylint: disable=import-error,duplicate-code
"""Paperang P2 Printer - Text platform.

Provides a text input entity for print content.
"""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up text platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = f"paperang_{entry.entry_id}"
    device_info = DeviceInfo(
        identifiers={("paperang", device_id)},
    )

    async_add_entities([
        PaperangPrintContent(coordinator, device_info, device_id),
    ])


class PaperangPrintContent(CoordinatorEntity, TextEntity):
    """Text input for print content (text, URL, or QR data)."""

    _attr_has_entity_name = True
    _attr_mode = "text"

    def __init__(self, coordinator, device_info, device_id) -> None:
        """Initialize."""
        self._attr_name = "Print Content"
        self._attr_unique_id = f"{device_id}_print_content"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:form-textbox"
        self._attr_native_value = ""
        super().__init__(coordinator)

    async def async_set_value(self, value: str) -> None:
        """Set text value."""
        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
