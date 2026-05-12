"""Paperang P2 Printer - Sensor platform.

Provides battery, status, voltage, temperature, and other printer telemetry
via periodic USB polling.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import timedelta
from functools import partial

import usb.util
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

# Handle paperang module path conflict (lib shares name with this integration)
# pylint: disable=wrong-import-position, wrong-import-order
_custom = [p for p in sys.path if "custom_components" in p]
for p in _custom:
    sys.path.remove(p)
import paperang as _lib

for p in _custom:
    sys.path.insert(0, p)

PaperangP2 = _lib.PaperangP2  # pylint: disable=no-member

DEVICE_ID = "paperang_p2_printer"
DEVICE_INFO = DeviceInfo(
    identifiers={("paperang", DEVICE_ID)},
    name="Paperang P2 Printer",
    manufacturer="Paperang",
    model="P2",
)

SCAN_INTERVAL = timedelta(seconds=60)


async def _read_printer_state(hass):
    """Read all printer telemetry (runs blocking USB in executor)."""
    return await hass.async_add_executor_job(_do_read_printer_state)


# pylint: disable=duplicate-code
_static_data: dict[str, object] = {}


def _do_read_printer_state():
    """Blocking: connect to printer and read telemetry.

    Always reads battery + status (dynamic).
    Static fields (voltage, temperature, firmware, etc.) are read once
    on first connect or reconnect, then cached until disconnection.
    """
    data = {"available": False}
    printer = PaperangP2()
    try:
        printer.connect()

        # Always read dynamic values
        data["battery"] = printer.get_battery()
        time.sleep(0.2)
        data["status"] = printer.get_status()

        if _static_data:
            # Device already online: reuse cached static values
            data.update(_static_data)
        else:
            # First connect or reconnecting after failure: read everything
            time.sleep(0.2)
            data["voltage"] = printer.get_voltage()
            time.sleep(0.2)
            data["temperature"] = printer.get_temperature()
            time.sleep(0.2)
            data["heat_density"] = printer.get_heat_density()
            time.sleep(0.2)
            data["paper_type"] = printer.get_paper_type()
            time.sleep(0.2)
            data["version"] = printer.get_version()
            time.sleep(0.2)
            data["model"] = printer.get_model()
            time.sleep(0.2)
            data["serial"] = printer.get_sn()
            time.sleep(0.2)
            data["board"] = printer.get_board_version()
            time.sleep(0.2)
            data["hw_info"] = printer.get_hw_info()

            # Cache static fields for subsequent polls
            _static_data.clear()
            _static_data.update({
                k: v for k, v in data.items()
                if k not in ("battery", "status", "available")
            })

        data["available"] = True
    except Exception as err:
        _LOGGER.debug("Printer not available: %s", err)
        _static_data.clear()  # Clear cache to force re-read on next connect
    finally:
        if printer.dev:
            try:
                usb.util.dispose_resources(printer.dev)
            except Exception:
                pass
    return data
# pylint: enable=duplicate-code


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Paperang sensors."""
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="paperang",
        update_method=partial(_read_printer_state, hass),
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_refresh()
    _LOGGER.info("Paperang coordinator data: %s", coordinator.data)

    async_add_entities([
        PaperangSensor(coordinator, "battery", "Battery", "mdi:battery",
                       device_class="battery", unit=PERCENTAGE, state_class="measurement"),
        PaperangSensor(coordinator, "status", "Status", "mdi:printer"),
        PaperangSensor(coordinator, "voltage", "Voltage", "mdi:flash",
                       device_class="voltage", unit=UnitOfElectricPotential.MILLIVOLT, state_class="measurement"),
        PaperangSensor(coordinator, "temperature", "Temperature", "mdi:thermometer",
                       device_class="temperature", unit=UnitOfTemperature.CELSIUS, state_class="measurement"),
        PaperangSensor(coordinator, "heat_density", "Heat Density", "mdi:thermometer-lines",
                       device_class=None, unit=PERCENTAGE, state_class="measurement"),
        PaperangSensor(coordinator, "paper_type", "Paper Type", "mdi:paper-roll"),
        PaperangSensor(coordinator, "version", "Firmware Version", "mdi:information-outline"),
        PaperangSensor(coordinator, "model", "Model", "mdi:printer-3d-nozzle"),
        PaperangSensor(coordinator, "serial", "Serial Number", "mdi:barcode"),
        PaperangSensor(coordinator, "board", "Board Version", "mdi:chip"),
        PaperangSensor(coordinator, "hw_info", "Hardware Info", "mdi:memory"),
    ])


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up from config entry."""
    await async_setup_platform(hass, {}, async_add_entities)


class PaperangSensor(CoordinatorEntity, SensorEntity):
    """Generic Paperang sensor. Reads a key from coordinator data."""

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
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Paperang P2 {name}"
        self._attr_unique_id = f"paperang_p2_{key}"
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class

    @property
    def device_info(self) -> DeviceInfo:
        return DEVICE_INFO

    @property
    def native_value(self):
        data = self.coordinator.data
        if data and data.get("available"):
            return data.get(self._key)
        return None

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return data is not None and data.get("available", False)
