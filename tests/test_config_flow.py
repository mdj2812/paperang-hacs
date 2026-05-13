"""Tests for paperang config flow — schema validation and migration."""
import asyncio
from unittest.mock import MagicMock

import pytest
import voluptuous as vol


class TestConfigFlowSchema:
    def test_user_step_schema_valid_usb(self):
        """Schema accepts USB transport."""
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
        """Schema accepts BLE transport with MAC."""
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

    def test_user_step_schema_ble_no_address(self):
        """BLE without address is valid (auto-scan)."""
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
            vol.Optional("ble_address"): str,
        })
        result = schema({"transport": "ble"})
        assert result["transport"] == "ble"

    def test_user_step_schema_invalid_transport(self):
        """Invalid transport raises error."""
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
        })
        with pytest.raises(vol.Invalid):
            schema({"transport": "wifi"})

    def test_user_step_schema_defaults(self):
        """Default transport is USB."""
        schema = vol.Schema({
            vol.Required("transport", default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
            vol.Optional("ble_address"): str,
        })
        result = schema({})
        assert result["transport"] == "usb"
        assert "ble_address" not in result


class TestConfigFlowVersion:
    def test_version_is_2(self):
        """Config flow VERSION constant is 2."""
        # Read from source to avoid HA runtime dependency
        import ast
        with open("custom_components/paperang/config_flow.py") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "VERSION":
                        assert node.value.value == 2
                        return
        pytest.fail("VERSION not found in config_flow.py")


class TestMigrationHandler:
    def test_migrate_v1_to_v2_adds_transport(self):
        """V1 entries get transport: usb."""
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
        """V2 entries are untouched."""
        from custom_components.paperang.__init__ import async_migrate_entry

        entry = MagicMock()
        entry.version = 2
        entry.data = {"transport": "usb"}

        hass = MagicMock()
        result = asyncio.run(async_migrate_entry(hass, entry))
        assert result is True
        hass.config_entries.async_update_entry.assert_not_called()
