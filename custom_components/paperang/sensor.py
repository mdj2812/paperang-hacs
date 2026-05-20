"""Paperang P2 Printer - Sensor platform.

Provides real-time sensors (battery, status, voltage, temperature,
heat density) and diagnostic sensors (board revision, firmware, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .entity import PaperangEntity


@dataclass(frozen=True)
class SensorConfig:
    """Sensor-specific configuration (icon, HA sensor attrs, category)."""

    icon: str
    device_class: str | None = None
    unit: str | None = None
    state_class: str | None = None
    entity_category: EntityCategory | None = None


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = f"paperang_{entry.entry_id}"
    device_info = DeviceInfo(
        identifiers={("paperang", device_id)},
        name=entry.title,
        manufacturer="Paperang",
        model="P2",
    )

    async_add_entities(
        [
            # ── Live sensors ─────────────────────────────────────
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "battery",
                "Battery",
                config=SensorConfig(
                    icon="mdi:battery",
                    device_class="battery",
                    unit=PERCENTAGE,
                    state_class="measurement",
                ),
            ),
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "status",
                "Status",
                config=SensorConfig(icon="mdi:printer"),
            ),
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "voltage",
                "Voltage",
                config=SensorConfig(
                    icon="mdi:flash",
                    device_class="voltage",
                    unit=UnitOfElectricPotential.MILLIVOLT,
                    state_class="measurement",
                ),
            ),
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "temperature",
                "Temperature",
                config=SensorConfig(
                    icon="mdi:thermometer",
                    device_class="temperature",
                    unit=UnitOfTemperature.CELSIUS,
                    state_class="measurement",
                ),
            ),
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "heat_density",
                "Heat Density",
                config=SensorConfig(
                    icon="mdi:thermometer-lines",
                    unit=PERCENTAGE,
                    state_class="measurement",
                ),
            ),
            # ── Diagnostic sensors ───────────────────────────────
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "board",
                "Board Version",
                config=SensorConfig(
                    icon="mdi:chip", entity_category=EntityCategory.DIAGNOSTIC
                ),
            ),
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "version",
                "Firmware Version",
                config=SensorConfig(
                    icon="mdi:information-outline",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
            ),
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "hw_info",
                "Hardware Info",
                config=SensorConfig(
                    icon="mdi:memory", entity_category=EntityCategory.DIAGNOSTIC
                ),
            ),
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "model",
                "Model",
                config=SensorConfig(
                    icon="mdi:printer-3d-nozzle",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
            ),
            PaperangSensor(
                coordinator,
                device_id,
                device_info,
                "serial",
                "Serial Number",
                config=SensorConfig(
                    icon="mdi:barcode", entity_category=EntityCategory.DIAGNOSTIC
                ),
            ),
        ]
    )


class PaperangSensor(PaperangEntity, SensorEntity):
    """Generic Paperang sensor. Reads a key from coordinator data."""

    def __init__(
        self,
        coordinator,
        device_id: str,
        device_info: DeviceInfo,
        key: str,
        name: str,
        *,
        config: SensorConfig,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            name,
            f"{device_id}_{key}",
            config.icon,
            device_info=device_info,
            entry_id=device_id,
        )
        self._key = key
        self._attr_device_class = config.device_class
        self._attr_native_unit_of_measurement = config.unit
        self._attr_state_class = config.state_class
        self._attr_entity_category = config.entity_category

    @property
    def native_value(self):
        """Return current sensor value from coordinator data."""
        data = self.coordinator.data
        if data and data.get("available"):
            return data.get(self._key)
        return None

    @property
    def available(self) -> bool:
        """Return True if printer is available."""
        data = self.coordinator.data
        return data is not None and data.get("available", False)
