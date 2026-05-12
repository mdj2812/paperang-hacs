# pylint: disable=import-error
"""Paperang P2 Printer - Button platform.

Provides pressable buttons on the device page for printer actions.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

DEVICE_ID = "paperang_p2_printer"
DEVICE_INFO = DeviceInfo(
    identifiers={("paperang", DEVICE_ID)},
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        PaperangButton(coordinator, "feed_paper", "Feed Paper",
                       "mdi:arrow-down-bold"),
        PaperangButton(coordinator, "test_print", "Test Print",
                       "mdi:printer-check"),
    ])


class PaperangButton(CoordinatorEntity, ButtonEntity):
    """Button that triggers a printer action."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        action: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the button."""
        self._action = action
        self._attr_name = name
        self._attr_unique_id = f"paperang_p2_btn_{action}"
        self._attr_device_info = DEVICE_INFO
        self._attr_icon = icon
        super().__init__(coordinator)

    async def async_press(self) -> None:
        """Handle the button press."""
        if self._action == "feed_paper":
            await self.hass.services.async_call(
                DOMAIN, "feed_paper", {"lines": 50}, blocking=False,
            )
        elif self._action == "test_print":
            await self.hass.services.async_call(
                DOMAIN, "print_test_page", {}, blocking=False,
            )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
