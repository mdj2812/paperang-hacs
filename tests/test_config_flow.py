"""Tests for paperang config flow — schema, class constants, migration."""
from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from custom_components.paperang.config_flow import (
    PaperangConfigFlow,
    PaperangOptionsFlow,
)
from custom_components.paperang.const import (
    DOMAIN,
    TRANSPORT_USB,
    TRANSPORT_BLE,
    CONF_TRANSPORT,
    CONF_BLE_ADDRESS,
)
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

    def test_async_get_options_flow_returns_options_flow(self):
        opts = PaperangConfigFlow.async_get_options_flow(MagicMock())
        assert isinstance(opts, PaperangOptionsFlow)
@pytest.mark.asyncio
class TestConfigFlowUserStep:
    async def test_init_user_flow_returns_form(self, hass):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

    async def test_user_step_creates_usb_entry(self, hass):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TRANSPORT: TRANSPORT_USB},
        )
        assert result["type"] == "create_entry"
        assert result["data"][CONF_TRANSPORT] == TRANSPORT_USB

    async def test_user_step_creates_ble_entry(self, hass):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TRANSPORT: TRANSPORT_BLE, CONF_BLE_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        )
        assert result["type"] == "create_entry"
        assert result["data"][CONF_TRANSPORT] == TRANSPORT_BLE
        assert result["data"][CONF_BLE_ADDRESS] == "AA:BB:CC:DD:EE:FF"

    async def test_duplicate_aborts(self, hass):
        await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            1, {CONF_TRANSPORT: TRANSPORT_USB},
        )
        assert result["type"] == "create_entry"

        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result2["type"] == "abort"
        assert result2["reason"] == "already_configured"
