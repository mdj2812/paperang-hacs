"""Tests for paperang config flow — HA core style."""
from unittest.mock import MagicMock, patch

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
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from tests.common import MockConfigEntry


pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


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


async def test_user_flow_creates_usb_entry(hass: HomeAssistant) -> None:
    """User flow: select USB → create entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TRANSPORT: TRANSPORT_USB},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TRANSPORT] == TRANSPORT_USB


async def test_user_flow_creates_ble_entry(hass: HomeAssistant) -> None:
    """User flow: select BLE → create entry with MAC."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TRANSPORT: TRANSPORT_BLE, CONF_BLE_ADDRESS: "AA:BB:CC:DD:EE:FF"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TRANSPORT] == TRANSPORT_BLE
    assert result["data"][CONF_BLE_ADDRESS] == "AA:BB:CC:DD:EE:FF"


async def test_duplicate_usb_aborts(hass: HomeAssistant) -> None:
    """Second USB entry aborts."""
    MockConfigEntry(domain=DOMAIN, unique_id="paperang_p2_usb").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_duplicate_ble_aborts(hass: HomeAssistant) -> None:
    """Second BLE entry aborts."""
    MockConfigEntry(domain=DOMAIN, unique_id="paperang_p2_ble").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
