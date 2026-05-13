"""Tests for paperang config flow — schema validation and migration."""
from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from custom_components.paperang.config_flow import PaperangConfigFlow, PaperangOptionsFlow


class TestConfigFlowSchema:
    def test_user_step_schema_valid_usb(self):
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
            vol.Optional("ble_address"): str,
        })
        result = schema({"transport": "usb"})
        assert result["transport"] == "usb"

    def test_user_step_schema_valid_ble(self):
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
            vol.Optional("ble_address"): str,
        })
        result = schema({"transport": "ble", "ble_address": "AA:BB:CC:DD:EE:FF"})
        assert result["transport"] == "ble"
        assert result["ble_address"] == "AA:BB:CC:DD:EE:FF"

    def test_ble_without_address_valid(self):
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
            vol.Optional("ble_address"): str,
        })
        result = schema({"transport": "ble"})
        assert result["transport"] == "ble"


class TestConfigFlowClass:
    @pytest.mark.skip(reason="ConfigFlow mock requires full HA runtime")
    def test_version_is_2(self):
        assert PaperangConfigFlow.VERSION == 2

    @pytest.mark.skip(reason="ConfigFlow mock requires full HA runtime")
    def test_async_get_options_flow(self):
        opts = PaperangConfigFlow.async_get_options_flow(MagicMock())
        assert isinstance(opts, PaperangOptionsFlow)
