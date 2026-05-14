"""Paperang P2 Printer - Sensor platform.

Provides battery, status, voltage, temperature, and other printer telemetry
via periodic USB polling.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfTemperature,
)

from .const import DOMAIN
from .entity import PaperangEntity


@dataclass(frozen=True)
class SensorConfig:
    """Optional sensor configuration."""

    device_class: str | None = None
    unit: str | None = None
    state_class: str | None = None


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PaperangSensor(coordinator, "battery", "Battery", "mdi:battery",
                       config=SensorConfig(device_class="battery", unit=PERCENTAGE,
                                           state_class="measurement")),
        PaperangSensor(coordinator, "status", "Status", "mdi:printer"),
        PaperangSensor(coordinator, "voltage", "Voltage", "mdi:flash",
                       config=SensorConfig(device_class="voltage",
                                           unit=UnitOfElectricPotential.MILLIVOLT,
                                           state_class="measurement")),
        PaperangSensor(coordinator, "temperature", "Temperature", "mdi:thermometer",
                       config=SensorConfig(device_class="temperature",
                                           unit=UnitOfTemperature.CELSIUS,
                                           state_class="measurement")),
        PaperangSensor(coordinator, "heat_density", "Heat Density", "mdi:thermometer-lines",
                       config=SensorConfig(unit=PERCENTAGE, state_class="measurement")),
        PaperangSensor(coordinator, "paper_type", "Paper Type", "mdi:paper-roll"),
        PaperangSensor(coordinator, "version", "Firmware Version", "mdi:information-outline"),
        PaperangSensor(coordinator, "model", "Model", "mdi:printer-3d-nozzle"),
        PaperangSensor(coordinator, "serial", "Serial Number", "mdi:barcode"),
        PaperangSensor(coordinator, "board", "Board Version", "mdi:chip"),
        PaperangSensor(coordinator, "hw_info", "Hardware Info", "mdi:memory"),
    ])


class PaperangSensor(PaperangEntity, SensorEntity):
    """Generic Paperang sensor. Reads a key from coordinator data."""

    def __init__(
        self,
        coordinator,
        key: str,
        name: str,
        icon: str,
        *,
        config: SensorConfig | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, name, f"paperang_p2_{key}", icon)
        self._key = key
        if config is None:
            config = SensorConfig()
        self._attr_device_class = config.device_class
        self._attr_native_unit_of_measurement = config.unit
        self._attr_state_class = config.state_class

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
