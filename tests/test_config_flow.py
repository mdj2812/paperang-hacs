"""Tests for paperang config flow — HA core style."""
from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    """Second BLE entry aborts when user selects BLE."""
    MockConfigEntry(domain=DOMAIN, unique_id="paperang_p2_ble").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    # First step shows form (USB is still available)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TRANSPORT: TRANSPORT_BLE, CONF_BLE_ADDRESS: "AA:BB:CC:DD:EE:FF"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ── USB discovery, import, both-configured, options flow ──────────

async def test_both_transports_configured_aborts(hass: HomeAssistant) -> None:
    """When both USB and BLE are configured, abort immediately."""
    MockConfigEntry(domain=DOMAIN, unique_id="paperang_p2_usb").add_to_hass(hass)
    MockConfigEntry(domain=DOMAIN, unique_id="paperang_p2_ble").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_usb_discovery_flow(hass: HomeAssistant) -> None:
    """USB discovery shows confirm step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"


async def test_usb_discovery_confirm_creates_entry(hass: HomeAssistant) -> None:
    """Confirm USB discovery creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "usb"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TRANSPORT] == TRANSPORT_USB


async def test_import_flow(hass: HomeAssistant) -> None:
    """YAML import delegates to user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "import"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_options_flow_show_form(hass: HomeAssistant) -> None:
    """Options flow shows the init form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TRANSPORT: TRANSPORT_USB},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_save(hass: HomeAssistant) -> None:
    """Options flow saves new config."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TRANSPORT: TRANSPORT_USB},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_TRANSPORT: TRANSPORT_BLE, CONF_BLE_ADDRESS: "11:22:33:44:55:66"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TRANSPORT] == TRANSPORT_BLE
