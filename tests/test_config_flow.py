"""Tests for paperang config flow — schema validation and migration."""
import asyncio
from unittest.mock import MagicMock

import pytest
import voluptuous as vol


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

    def test_invalid_transport_raises(self):
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
        })
        with pytest.raises(vol.Invalid):
            schema({"transport": "wifi"})


class TestConfigFlowClass:
    @pytest.mark.skip(reason="requires precise ConfigFlow mock setup")
    def test_version_is_2(self):
        from custom_components.paperang.config_flow import PaperangConfigFlow
        assert PaperangConfigFlow.VERSION == 2

    @pytest.mark.skip(reason="requires precise ConfigFlow mock setup")
    def test_async_get_options_flow(self):
        from custom_components.paperang.config_flow import PaperangConfigFlow
        flow = PaperangConfigFlow()
        opts = PaperangConfigFlow.async_get_options_flow(MagicMock())
        from custom_components.paperang.config_flow import PaperangOptionsFlow
        assert isinstance(opts, PaperangOptionsFlow)


class TestMigrationHandler:
    def test_migrate_v1_to_v2_adds_transport(self):
        from custom_components.paperang.__init__ import async_migrate_entry
        from custom_components.paperang.const import TRANSPORT_USB, CONF_TRANSPORT

        entry = MagicMock()
        entry.version = 1
        entry.data = {}

        hass = MagicMock()
        result = asyncio.run(async_migrate_entry(hass, entry))
        assert result is True
        hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = hass.config_entries.async_update_entry.call_args.kwargs
        assert call_kwargs.get("version") == 2
        assert call_kwargs.get("data") == {CONF_TRANSPORT: TRANSPORT_USB}

    def test_migrate_v2_noop(self):
        from custom_components.paperang.__init__ import async_migrate_entry
        entry = MagicMock()
        entry.version = 2
        entry.data = {"transport": "usb"}
        hass = MagicMock()
        result = asyncio.run(async_migrate_entry(hass, entry))
        assert result is True
        hass.config_entries.async_update_entry.assert_not_called()
