"""E2E tests for Paperang config flow — real HA Core, mock transport layer.

These tests exercise the full config flow lifecycle:
- USB device discovery → select → verify → create entry
- BT device discovery → select → verify → create entry
- Options flow
- Config entry migration v1 → v2
"""

from unittest.mock import patch

import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import (
    CONF_BT_ADDRESS,
    CONF_TRANSPORT,
    CONF_USB_BUS,
    CONF_USB_PORT,
    DOMAIN,
    TRANSPORT_BT,
    TRANSPORT_USB,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

# Patch targets must match the local import aliases in config_flow.py:
#   from .transport.usb import scan_usb_devices as _scan_usb_devices
#   from .transport.usb import verify_printer as _verify_printer
#   from .transport.bt import scan_bt_devices as _scan_bt_devices
#   from .transport.bt import verify_bt_printer as _verify_bt_printer
_PATCH_USB_SCAN = "custom_components.paperang.config_flow._scan_usb_devices"
_PATCH_USB_VERIFY = "custom_components.paperang.config_flow._verify_printer"
_PATCH_BT_SCAN = "custom_components.paperang.config_flow._scan_bt_devices"
_PATCH_BT_VERIFY = "custom_components.paperang.config_flow._verify_bt_printer"

# ── Mock USB scan data ────────────────────────────────────────────
FAKE_USB_DEVICES = [
    {
        "usb_path": "1-3",
        "bus": 1,
        "port": 3,
        "address": 5,
        "vid": "4348",
        "pid": "5584",
        "manufacturer": "wch.cn",
        "description": "USB Serial",
    },
    {
        "usb_path": "2-1",
        "bus": 2,
        "port": 1,
        "address": 3,
        "vid": "4348",
        "pid": "5584",
        "manufacturer": "wch.cn",
        "description": "USB Serial",
    },
]

# ── Mock BT scan data ─────────────────────────────────────────────
FAKE_BT_DEVICES = [
    {"address": "00:15:83:EB:05:17", "name": "Paperang_P2"},
    {"address": "00:15:83:AB:12:34", "name": "Paperang_P2"},
    {"address": "DC:0D:30:AA:BB:CC", "name": "Paperang_Office"},
]


class TestConfigFlowUSB:
    """USB config flow — single device (auto-select)."""

    async def test_usb_single_device_auto_select(self, hass: HomeAssistant) -> None:
        """Single USB device → skip select → verify → create entry."""
        with (
            patch(_PATCH_USB_SCAN, return_value=FAKE_USB_DEVICES[:1]),
            patch(_PATCH_USB_VERIFY, return_value=True),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert result["title"] == "Paperang P2 (USB 1-3)"
            assert result["data"][CONF_TRANSPORT] == TRANSPORT_USB
            assert result["data"][CONF_USB_BUS] == 1
            assert result["data"][CONF_USB_PORT] == 3
            assert result["result"].unique_id == "paperang_usb_1-3"

    async def test_usb_single_device_verify_fails(self, hass: HomeAssistant) -> None:
        """Verify fails → shows form with error."""
        with (
            patch(_PATCH_USB_SCAN, return_value=FAKE_USB_DEVICES[:1]),
            patch(_PATCH_USB_VERIFY, return_value=False),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "usb_verify"
            assert result["errors"] == {"base": "communication_failed"}

    async def test_usb_no_devices_aborts(self, hass: HomeAssistant) -> None:
        """No USB devices found → abort."""
        with patch(_PATCH_USB_SCAN, return_value=[]):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["type"] == data_entry_flow.FlowResultType.ABORT
            assert result["reason"] == "no_usb_device_found"


class TestConfigFlowUSBMulti:
    """USB config flow — multiple devices (user picks)."""

    async def test_usb_multi_device_select_then_verify(
        self, hass: HomeAssistant
    ) -> None:
        """Multiple USB devices → select_device → pick → verify → create."""
        with (
            patch(_PATCH_USB_SCAN, return_value=FAKE_USB_DEVICES),
            patch(_PATCH_USB_VERIFY, return_value=True),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "select_device"

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"usb_device": "2-1"},
            )
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert result["title"] == "Paperang P2 (USB 2-1)"
            assert result["data"][CONF_USB_BUS] == 2
            assert result["data"][CONF_USB_PORT] == 1

    async def test_usb_multi_device_select_invalid(self, hass: HomeAssistant) -> None:
        """Select a device not in the list → raises InvalidData."""
        import voluptuous as vol

        with patch(_PATCH_USB_SCAN, return_value=FAKE_USB_DEVICES):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["step_id"] == "select_device"

            with pytest.raises(vol.Invalid):
                await hass.config_entries.flow.async_configure(
                    result["flow_id"],
                    {"usb_device": "9-9"},
                )


class TestConfigFlowBT:
    """BT config flow — scan, select, verify, create."""

    async def test_bt_single_device_auto_select(self, hass: HomeAssistant) -> None:
        """Single BT device → auto-skip select → verify → create entry."""
        with (
            patch(_PATCH_BT_SCAN, return_value=FAKE_BT_DEVICES[:1]),
            patch(_PATCH_BT_VERIFY, return_value=True),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "classic_bluetooth"}
            )
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert "Paperang P2" in result["title"]
            assert result["data"][CONF_TRANSPORT] == TRANSPORT_BT
            assert result["data"][CONF_BT_ADDRESS] == "00:15:83:EB:05:17"

    async def test_bt_no_devices_aborts(self, hass: HomeAssistant) -> None:
        """No BT devices found → abort."""
        with patch(_PATCH_BT_SCAN, return_value=[]):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "classic_bluetooth"}
            )
            assert result["type"] == data_entry_flow.FlowResultType.ABORT


class TestConfigFlowUser:
    """User-initiated config flow (manual setup)."""

    async def test_user_flow_selects_usb(self, hass: HomeAssistant) -> None:
        """User flow → pick USB transport → scan → verify → create."""
        with (
            patch(_PATCH_USB_SCAN, return_value=FAKE_USB_DEVICES[:1]),
            patch(_PATCH_USB_VERIFY, return_value=True),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "user"

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_TRANSPORT: TRANSPORT_USB},
            )
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


class TestConfigFlowMigration:
    """Config entry migration v1 → v2."""

    async def test_migrate_v1_to_v2_adds_transport(self, hass: HomeAssistant) -> None:
        """v1 entry without transport key gets TRANSPORT_USB added."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"usb_path": "1-3"},
            version=1,
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod

        result = await mod.async_migrate_entry(hass, entry)
        assert result is True
        assert entry.version == 2
        assert entry.data[CONF_TRANSPORT] == TRANSPORT_USB

    async def test_migrate_v2_noop(self, hass: HomeAssistant) -> None:
        """v2 entry is left unchanged."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB, "usb_path": "1-3"},
            version=2,
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod

        result = await mod.async_migrate_entry(hass, entry)
        assert result is True
        assert entry.version == 2
        assert entry.data[CONF_TRANSPORT] == TRANSPORT_USB


class TestConfigFlowOptions:
    """Options flow for existing config entries."""

    async def test_options_flow_shows_form(self, hass: HomeAssistant) -> None:
        """Options flow shows transport form."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB, CONF_USB_BUS: 1, CONF_USB_PORT: 3},
            version=2,
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] in (
            data_entry_flow.FlowResultType.FORM,
            data_entry_flow.FlowResultType.MENU,
        )

    async def test_duplicate_entry_blocked(self, hass: HomeAssistant) -> None:
        """Second entry with same unique_id is aborted."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB, CONF_USB_BUS: 1, CONF_USB_PORT: 3},
            unique_id="paperang_usb_1-3",
            version=2,
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        with (
            patch(_PATCH_USB_SCAN, return_value=FAKE_USB_DEVICES[:1]),
            patch(_PATCH_USB_VERIFY, return_value=True),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["type"] == data_entry_flow.FlowResultType.ABORT
            assert result["reason"] == "already_configured"
