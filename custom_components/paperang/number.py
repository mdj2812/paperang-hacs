"""Paperang P2 Printer - Number platform.

Provides configurable numeric controls for print parameters.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE

from .const import DOMAIN
from .entity import PaperangEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up number platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        PaperangNumber(coordinator, "font_size", "Font Size",
                       icon="mdi:format-size", minimum=12, maximum=96,
                       default=24, step=1, unit=None),
        PaperangNumber(coordinator, "heat_density", "Heat Density",
                       icon="mdi:thermometer", minimum=0, maximum=100,
                       default=75, step=5, unit=PERCENTAGE),
        PaperangNumber(coordinator, "qr_size", "QR Size",
                       icon="mdi:qrcode", minimum=100, maximum=576,
                       default=500, step=10, unit="px"),
        PaperangNumber(coordinator, "feed_lines", "Feed Lines",
                       icon="mdi:format-line-spacing", minimum=10, maximum=500,
                       default=50, step=10, unit="lines"),
    ])


class PaperangNumber(PaperangEntity, NumberEntity):
    """Configurable numeric control for print parameters."""

    def __init__(
        self,
        coordinator,
        key: str,
        name: str,
        *,
        icon: str,
        minimum: float,
        maximum: float,
        default: float,
        step: float,
        unit: str | None,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, name, f"paperang_p2_num_{key}", icon)
        self._key = key
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = default

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        self._attr_native_value = value
        self.async_write_ha_state()
