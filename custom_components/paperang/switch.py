"""Paperang P2 Printer - Switch platform.

Provides a toggle switch for vertical printing mode.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .entity import PaperangEntity, make_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up switch platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_info = make_device_info(entry)

    async_add_entities(
        [
            PaperangVerticalSwitch(coordinator, entry.entry_id, device_info),
        ]
    )


class PaperangVerticalSwitch(PaperangEntity, SwitchEntity):
    """Toggle vertical printing mode."""

    def __init__(self, coordinator, entry_id, device_info) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            entry_id,
            "Vertical",
            "vertical",
            "mdi:rotate-right",
            device_info=device_info,
        )
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on vertical printing."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off vertical printing."""
        self._attr_is_on = False
        self.async_write_ha_state()
