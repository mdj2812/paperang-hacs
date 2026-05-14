# pylint: disable=import-error
"""Paperang P2 Printer - Number platform.

Provides configurable numeric controls for print parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE

from .const import DOMAIN
from .entity import PaperangEntity


@dataclass(frozen=True)
class NumberRange:
    """Numeric range + icon configuration for a PaperangNumber entity."""

    icon: str
    minimum: float
    maximum: float
    default: float
    step: float
    unit: str | None = None


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up number platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        PaperangNumber(coordinator, "font_size", "Font Size",
                       num_range=NumberRange(icon="mdi:format-size",
                                             minimum=12, maximum=96, default=24, step=1)),
        PaperangNumber(coordinator, "heat_density", "Heat Density",
                       num_range=NumberRange(icon="mdi:thermometer",
                                             minimum=0, maximum=100, default=75, step=5,
                                             unit=PERCENTAGE)),
        PaperangNumber(coordinator, "qr_size", "QR Size",
                       num_range=NumberRange(icon="mdi:qrcode",
                                             minimum=100, maximum=576, default=500, step=10,
                                             unit="px")),
        PaperangNumber(coordinator, "feed_lines", "Feed Lines",
                       num_range=NumberRange(icon="mdi:format-line-spacing",
                                             minimum=10, maximum=500, default=50, step=10,
                                             unit="lines")),
    ])


class PaperangNumber(PaperangEntity, NumberEntity):
    """Configurable numeric control for print parameters."""

    def __init__(
        self,
        coordinator,
        key: str,
        name: str,
        *,
        num_range: NumberRange,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, name, f"paperang_p2_num_{key}", num_range.icon)
        self._key = key
        self._attr_native_min_value = num_range.minimum
        self._attr_native_max_value = num_range.maximum
        self._attr_native_step = num_range.step
        self._attr_native_unit_of_measurement = num_range.unit
        self._attr_native_value = num_range.default

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        self._attr_native_value = value
        self.async_write_ha_state()
