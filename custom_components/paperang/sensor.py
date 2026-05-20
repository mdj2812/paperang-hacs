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


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_name = entry.title
    device_id = f"paperang_{entry.entry_id}"
    device_info = DeviceInfo(
        identifiers={("paperang", device_id)},
        name=device_name,
        manufacturer="Paperang",
        model="P2",
    )
    async_add_entities([
        PaperangSensor(coordinator, device_info, device_id, "battery", "Battery", "mdi:battery",
                       device_class="battery", unit=PERCENTAGE, state_class="measurement"),
        PaperangSensor(coordinator, device_info, device_id, "status", "Status", "mdi:printer"),
        PaperangSensor(coordinator, device_info, device_id, "voltage", "Voltage", "mdi:flash",
                       device_class="voltage",
                       unit=UnitOfElectricPotential.MILLIVOLT,
                       state_class="measurement"),
        PaperangSensor(coordinator, device_info, device_id, "temperature", "Temperature", "mdi:thermometer",
                       device_class="temperature",
                       unit=UnitOfTemperature.CELSIUS,
                       state_class="measurement"),
        PaperangSensor(coordinator, device_info, device_id, "heat_density", "Heat Density", "mdi:thermometer-lines",
                       device_class=None, unit=PERCENTAGE, state_class="measurement"),
        PaperangSensor(coordinator, device_info, device_id, "paper_type", "Paper Type", "mdi:paper-roll"),
        PaperangSensor(coordinator, device_info, device_id, "version", "Firmware Version", "mdi:information-outline"),
        PaperangSensor(coordinator, device_info, device_id, "model", "Model", "mdi:printer-3d-nozzle"),
        PaperangSensor(coordinator, device_info, device_id, "serial", "Serial Number", "mdi:barcode"),
        PaperangSensor(coordinator, device_info, device_id, "board", "Board Version", "mdi:chip"),
        PaperangSensor(coordinator, device_info, device_id, "hw_info", "Hardware Info", "mdi:memory"),
    ])


# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments
class PaperangSensor(CoordinatorEntity, SensorEntity):
    """Generic Paperang sensor. Reads a key from coordinator data."""

    _attr_has_entity_name = True

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_info: DeviceInfo,
        device_id: str,
        key: str,
        name: str,
        icon: str,
        *,
        device_class: str | None = None,
        unit: str | None = None,
        state_class: str | None = None,
    ) -> None:
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{key}"
        super().__init__(coordinator)
        self._key = key
        self._attr_device_info = device_info
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
