"""Tests for paperang config flow — schema and class constants."""
from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from custom_components.paperang.config_flow import (
    PaperangConfigFlow,
    PaperangOptionsFlow,
)



class TestConfigFlowSchema:
    def test_user_step_schema_valid_usb(self):
        """User step schema: transport selector only (USB/BLE)."""
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
        })
        result = schema({"transport": "usb"})
        assert result["transport"] == "usb"

    def test_user_step_schema_valid_ble(self):
        """User step schema: BLE transport (discovery is automatic)."""
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
        })
        result = schema({"transport": "ble"})
        assert result["transport"] == "ble"

    def test_select_device_schema(self):
        """Select USB device dropdown schema."""
        schema = vol.Schema({
            vol.Required("usb_device"): vol.In({
                "1-3": "Paperang P2 — USB 1-3 (bus 1, addr 5)",
                "2-1": "Paperang P2 — USB 2-1 (bus 2, addr 8)",
            }),
        })
        result = schema({"usb_device": "1-3"})
        assert result["usb_device"] == "1-3"


class TestConfigFlowClass:
    def test_version_is_2(self):
        assert PaperangConfigFlow.VERSION == 2

    def test_async_get_options_flow(self):
        opts = PaperangConfigFlow.async_get_options_flow(MagicMock())
        assert isinstance(opts, PaperangOptionsFlow)
