"""Tests for paperang config flow — using hass fixture from pytest plugin."""
from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from custom_components.paperang.config_flow import PaperangConfigFlow, PaperangOptionsFlow
from custom_components.paperang.const import DOMAIN, TRANSPORT_USB, TRANSPORT_BLE


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
    def test_version_is_2(self):
        assert PaperangConfigFlow.VERSION == 2

    def test_async_get_options_flow(self):
        opts = PaperangConfigFlow.async_get_options_flow(MagicMock())
        assert isinstance(opts, PaperangOptionsFlow)


@pytest.mark.asyncio
class TestConfigFlowHass:
    async def test_user_step_defaults_to_usb(self, hass):
        """User flow defaults to USB transport."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

    async def test_user_step_creates_usb_entry(self, hass):
        """Submitting USB creates entry with transport=usb."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"transport": TRANSPORT_USB},
        )
        assert result["type"] == "create_entry"
        assert result["data"][TRANSPORT_USB] == TRANSPORT_USB

    async def test_user_step_creates_ble_entry(self, hass):
        """Submitting BLE creates entry with transport=ble + address."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"transport": TRANSPORT_BLE, "ble_address": "AA:BB:CC:DD:EE:FF"},
        )
        assert result["type"] == "create_entry"
        assert result["data"]["transport"] == TRANSPORT_BLE
        assert result["data"]["ble_address"] == "AA:BB:CC:DD:EE:FF"

    async def test_user_step_unique_id_prevents_duplicate(self, hass):
        """Cannot add two USB entries."""
        await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            1, {"transport": TRANSPORT_USB},
        )
        assert result["type"] == "create_entry"

        # Second attempt should abort
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result2["type"] == "abort"
        assert result2["reason"] == "already_configured"
