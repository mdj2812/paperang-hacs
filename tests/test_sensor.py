"""Tests for paperang sensor platform — HA core style."""

import pytest
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfTemperature, EntityCategory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import DOMAIN

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def _setup_coordinator(hass: HomeAssistant, entry: MockConfigEntry, data=None):
    """Set up a config entry with a mock coordinator."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = data or {
        "available": True,
        "battery": 80,
        "status": "online",
        "voltage": 4200,
        "temperature": 35,
        "heat_density": 75,
        "board": "V1.0",
        "version": "V1.0.11",
        "hw_info": "ABC123",
        "model": "P2",
        "serial": "SN123456",
    }
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator


class TestSensors:
    async def test_all_sensors_created(self, hass: HomeAssistant) -> None:
        """All 10 sensors (5 live + 5 diagnostic) are created."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.sensor import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)
        await hass.async_block_till_done()

        add_entities.assert_called_once()
        entities = add_entities.call_args[0][0]
        assert len(entities) == 10

        for e in entities:
            assert e.unique_id.startswith(f"paperang_{entry.entry_id}_")
            assert e.device_info is not None

    async def test_sensor_attributes(self, hass: HomeAssistant) -> None:
        """Battery sensor has correct device class and unit."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.sensor import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        entities = add_entities.call_args[0][0]
        by_key = {e._key: e for e in entities}

        batt = by_key["battery"]
        assert batt.device_class == "battery"
        assert batt.native_unit_of_measurement == PERCENTAGE
        assert batt.state_class == "measurement"
        assert batt.native_value == 80

        volt = by_key["voltage"]
        assert volt.device_class == "voltage"
        assert volt.native_unit_of_measurement == UnitOfElectricPotential.MILLIVOLT
        assert volt.native_value == 4200

        temp = by_key["temperature"]
        assert temp.device_class == "temperature"
        assert temp.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert temp.native_value == 35

    async def test_diagnostic_sensors_category(self, hass: HomeAssistant) -> None:
        """Diagnostic sensors have EntityCategory.DIAGNOSTIC."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.sensor import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        entities = add_entities.call_args[0][0]
        by_key = {e._key: e for e in entities}

        assert by_key["battery"].entity_category is None
        assert by_key["status"].entity_category is None
        assert by_key["voltage"].entity_category is None
        assert by_key["board"].entity_category == EntityCategory.DIAGNOSTIC
        assert by_key["version"].entity_category == EntityCategory.DIAGNOSTIC
        assert by_key["hw_info"].entity_category == EntityCategory.DIAGNOSTIC
        assert by_key["model"].entity_category == EntityCategory.DIAGNOSTIC
        assert by_key["serial"].entity_category == EntityCategory.DIAGNOSTIC

    async def test_sensor_unavailable_when_printer_offline(self, hass: HomeAssistant) -> None:
        """Sensor shows unavailable when coordinator data signals offline."""
        entry = MockConfigEntry(domain=DOMAIN, title="Paperang P2 (USB 1-3)")
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry, data={"available": False})

        from custom_components.paperang.sensor import async_setup_entry

        add_entities = MagicMock()
        await async_setup_entry(hass, entry, add_entities)

        entities = add_entities.call_args[0][0]
        for e in entities:
            assert not e.available
