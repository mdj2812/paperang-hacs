# pylint: disable=import-error
"""Paperang P2 Printer - Number platform.

Provides configurable numeric controls for print parameters.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

DEVICE_ID = "paperang_p2_printer"
DEVICE_INFO = DeviceInfo(
    identifiers={("paperang", DEVICE_ID)},
)


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


class PaperangNumber(CoordinatorEntity, NumberEntity):  # pylint: disable=too-many-instance-attributes
    """Configurable numeric control for print parameters."""

    _attr_has_entity_name = True

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
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"paperang_p2_num_{key}"
        self._attr_device_info = DEVICE_INFO
        self._attr_icon = icon
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = default
        super().__init__(coordinator)

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
