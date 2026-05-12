# pylint: disable=import-error
"""Paperang P2 Printer - Sensor platform.

Provides battery, status, voltage, temperature, and other printer telemetry
via periodic USB polling.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

DEVICE_ID = "paperang_p2_printer"
DEVICE_INFO = DeviceInfo(
    identifiers={("paperang", DEVICE_ID)},
    name="Paperang P2 Printer",
    manufacturer="Paperang",
    model="P2",
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PaperangSensor(coordinator, "battery", "Battery", "mdi:battery",
                       device_class="battery", unit=PERCENTAGE, state_class="measurement"),
        PaperangSensor(coordinator, "status", "Status", "mdi:printer"),
        PaperangSensor(coordinator, "voltage", "Voltage", "mdi:flash",
                       device_class="voltage",
                       unit=UnitOfElectricPotential.MILLIVOLT,
                       state_class="measurement"),
        PaperangSensor(coordinator, "temperature", "Temperature", "mdi:thermometer",
                       device_class="temperature",
                       unit=UnitOfTemperature.CELSIUS,
                       state_class="measurement"),
        PaperangSensor(coordinator, "heat_density", "Heat Density", "mdi:thermometer-lines",
                       device_class=None, unit=PERCENTAGE, state_class="measurement"),
        PaperangSensor(coordinator, "paper_type", "Paper Type", "mdi:paper-roll"),
        PaperangSensor(coordinator, "version", "Firmware Version", "mdi:information-outline"),
        PaperangSensor(coordinator, "model", "Model", "mdi:printer-3d-nozzle"),
        PaperangSensor(coordinator, "serial", "Serial Number", "mdi:barcode"),
        PaperangSensor(coordinator, "board", "Board Version", "mdi:chip"),
        PaperangSensor(coordinator, "hw_info", "Hardware Info", "mdi:memory"),
    ])


class PaperangSensor(CoordinatorEntity, SensorEntity):  # pylint: disable=too-many-instance-attributes
    """Generic Paperang sensor. Reads a key from coordinator data."""

    _attr_has_entity_name = True

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        key: str,
        name: str,
        icon: str,
        *,
        device_class: str | None = None,
        unit: str | None = None,
        state_class: str | None = None,
    ) -> None:
        self._attr_name = name
        self._attr_unique_id = f"paperang_p2_{key}"
        super().__init__(coordinator)
        self._key = key
        self._attr_device_info = DEVICE_INFO
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class

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
