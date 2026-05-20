"""Tests for paperang config flow — HA integration style."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.paperang.config_flow import PaperangConfigFlow

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


class TestConfigFlowUSB:
    @pytest.mark.asyncio
    async def test_usb_step_no_devices_aborts(self, hass: HomeAssistant) -> None:
        """USB discovery aborts when no devices found."""
        flow = PaperangConfigFlow()
        flow.hass = hass

        with patch(
            "custom_components.paperang.config_flow._scan_usb_devices",
            return_value=[],
        ):
            result = await flow.async_step_usb()

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "no_usb_device_found"

    @pytest.mark.asyncio
    async def test_usb_step_multiple_devices_show_select(
        self, hass: HomeAssistant
    ) -> None:
        """Multiple USB devices show selection form."""
        flow = PaperangConfigFlow()
        flow.hass = hass

        devices = [
            {"usb_path": "1-3", "bus": 1, "port": [3], "address": 5},
            {"usb_path": "2-1", "bus": 2, "port": [1], "address": 8},
        ]

        with patch(
            "custom_components.paperang.config_flow._scan_usb_devices",
            return_value=devices,
        ):
            result = await flow.async_step_usb()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select_device"

    @pytest.mark.asyncio
    async def test_usb_select_device_form(self, hass: HomeAssistant) -> None:
        """Select device step shows dropdown form."""
        flow = PaperangConfigFlow()
        flow.hass = hass
        flow._usb_discovered = [
            {"usb_path": "1-3", "bus": 1, "port": [3], "address": 5},
        ]

        result = await flow.async_step_select_device()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select_device"


class TestConfigFlowBLE:
    @pytest.mark.asyncio
    async def test_ble_scan_no_devices_aborts(self, hass: HomeAssistant) -> None:
        """BLE step with no devices returns empty list from scan."""
        from custom_components.paperang.config_flow import _async_scan_ble_devices

        with patch("bleak.BleakScanner") as mock_cls:
            async def _empty(timeout=5):
                return []
            mock_cls.discover = _empty
            result = await _async_scan_ble_devices()

        assert result == []

    @pytest.mark.asyncio
    async def test_user_step_usb_no_devices_shows_error(
        self, hass: HomeAssistant
    ) -> None:
        """User step with USB and no devices shows error."""
        flow = PaperangConfigFlow()
        flow.hass = hass

        with patch(
            "custom_components.paperang.config_flow._scan_usb_devices",
            return_value=[],
        ):
            result = await flow.async_step_user({"transport": "usb"})

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "no_usb_device_found"

    @pytest.mark.asyncio
    async def test_user_step_ble_no_devices_shows_error(
        self, hass: HomeAssistant
    ) -> None:
        """User step with BLE shows ble_disabled error."""
        flow = PaperangConfigFlow()
        flow.hass = hass
        result = await flow.async_step_user({"transport": "ble"})
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "ble_disabled"
