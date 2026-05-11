"""Paperang P2 Printer - Sensor platform.

Provides battery level and printer status via periodic USB polling.
"""

from __future__ import annotations

import logging
import sys
from datetime import timedelta

import usb.util
from homeassistant.components.sensor import SensorEntity
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
    """Read battery and status from printer (runs blocking USB in executor)."""
    return await hass.async_add_executor_job(_do_read_printer_state)


# pylint: disable=duplicate-code
def _do_read_printer_state():
    """Blocking: connect to printer and read battery + status."""
    printer = PaperangP2()
    try:
        printer.connect()
        battery = printer.get_battery()
        status = printer.get_status()
        return {"battery": battery, "status": status, "available": True}
    except Exception as err:
        _LOGGER.debug("Printer not available: %s", err)
        return {"battery": None, "status": None, "available": False}
    finally:
        if printer.dev:
            try:
                usb.util.dispose_resources(printer.dev)
            except Exception:
                pass
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
        update_method=lambda: _read_printer_state(hass),
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data before adding entities
    await coordinator.async_refresh()
    _LOGGER.info("Paperang coordinator data after initial refresh: %s", coordinator.data)

    async_add_entities([
        PaperangBatterySensor(coordinator),
        PaperangStatusSensor(coordinator),
    ])


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up from config entry."""
    await async_setup_platform(hass, {}, async_add_entities)


class PaperangBatterySensor(CoordinatorEntity, SensorEntity):
    """Battery level sensor."""

    _attr_name = "Paperang P2 Battery"
    _attr_unique_id = "paperang_p2_battery"
    _attr_device_class = "battery"
    _attr_state_class = "measurement"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:battery"

    @property
    def device_info(self) -> DeviceInfo:
        return DEVICE_INFO

    @property
    def native_value(self):
        data = self.coordinator.data
        if data and data.get("available"):
            return data.get("battery")
        return None

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return data is not None and data.get("available", False)


class PaperangStatusSensor(CoordinatorEntity, SensorEntity):
    """Printer status sensor (raw hex)."""

    _attr_name = "Paperang P2 Status"
    _attr_unique_id = "paperang_p2_status"
    _attr_icon = "mdi:printer"

    @property
    def device_info(self) -> DeviceInfo:
        return DEVICE_INFO

    @property
    def native_value(self):
        data = self.coordinator.data
        if data and data.get("available"):
            return data.get("status")
        return None

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return data is not None and data.get("available", False)
