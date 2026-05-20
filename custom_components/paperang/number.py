"""Paperang P2 Printer - Number platform.

Provides configurable numeric controls for print parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE

from .const import DOMAIN
from .entity import PaperangEntity, make_device_info


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
    device_info = make_device_info(entry)

    async_add_entities(
        [
            PaperangNumber(
                coordinator, entry.entry_id, device_info,
                "font_size", "Font Size",
                num_range=NumberRange(
                    icon="mdi:format-size", minimum=12, maximum=96, default=24, step=1,
                ),
            ),
            PaperangNumber(
                coordinator, entry.entry_id, device_info,
                "heat_density", "Heat Density",
                num_range=NumberRange(
                    icon="mdi:thermometer", minimum=0, maximum=100, default=75,
                    step=5, unit=PERCENTAGE,
                ),
            ),
            PaperangNumber(
                coordinator, entry.entry_id, device_info,
                "qr_size", "QR Size",
                num_range=NumberRange(
                    icon="mdi:qrcode", minimum=100, maximum=576, default=500,
                    step=10, unit="px",
                ),
            ),
            PaperangNumber(
                coordinator, entry.entry_id, device_info,
                "feed_lines", "Feed Lines",
                num_range=NumberRange(
                    icon="mdi:format-line-spacing", minimum=10, maximum=500,
                    default=50, step=10, unit="lines",
                ),
            ),
        ]
    )


class PaperangNumber(PaperangEntity, NumberEntity):
    """Configurable numeric control for print parameters."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        coordinator,
        entry_id: str,
        device_info,
        key: str,
        name: str,
        *,
        num_range: NumberRange,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator, entry_id, name, f"num_{key}", num_range.icon,
            device_info=device_info,
        )
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
