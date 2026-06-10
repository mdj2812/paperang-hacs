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
]


class TestConfigFlowUSB:
    """USB config flow — single device (auto-select)."""

    async def test_usb_single_device_auto_select(self, hass: HomeAssistant) -> None:
        """Single USB device → skip select → verify → create entry."""
        with (
            patch(
                "custom_components.paperang.transport.usb.scan_usb_devices",
                return_value=FAKE_USB_DEVICES[:1],
            ),
            patch(
                "custom_components.paperang.transport.usb.verify_printer",
                return_value=True,
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            # Single device skips select_device, goes straight to usb_verify
            # The verify step shows a form on failure, but on success we
            # should get a create_entry result
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert result["title"] == "Paperang P2 (USB 1-3)"
            assert result["data"][CONF_TRANSPORT] == TRANSPORT_USB
            assert result["data"][CONF_USB_BUS] == 1
            assert result["data"][CONF_USB_PORT] == 3
            assert result["result"].unique_id == "paperang_usb_1-3"

    async def test_usb_single_device_verify_fails(self, hass: HomeAssistant) -> None:
        """Verify fails → shows form with error."""
        with (
            patch(
                "custom_components.paperang.transport.usb.scan_usb_devices",
                return_value=FAKE_USB_DEVICES[:1],
            ),
            patch(
                "custom_components.paperang.transport.usb.verify_printer",
                return_value=False,
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "usb_verify"
            assert result["errors"] == {"base": "communication_failed"}

    async def test_usb_no_devices_aborts(self, hass: HomeAssistant) -> None:
        """No USB devices found → abort."""
        with patch(
            "custom_components.paperang.transport.usb.scan_usb_devices",
            return_value=[],
        ):
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
        """Multiple USB devices → select_device → pick one → verify → create."""
        with (
            patch(
                "custom_components.paperang.transport.usb.scan_usb_devices",
                return_value=FAKE_USB_DEVICES,
            ),
            patch(
                "custom_components.paperang.transport.usb.verify_printer",
                return_value=True,
            ),
        ):
            # Step 1: start flow → should show select_device
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "select_device"

            # Step 2: pick device 2-1
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"usb_device": "2-1"},
            )
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert result["title"] == "Paperang P2 (USB 2-1)"
            assert result["data"][CONF_USB_BUS] == 2
            assert result["data"][CONF_USB_PORT] == 1

    async def test_usb_multi_device_select_invalid(self, hass: HomeAssistant) -> None:
        """Select a device not in the list → shows error."""
        with patch(
            "custom_components.paperang.transport.usb.scan_usb_devices",
            return_value=FAKE_USB_DEVICES,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            assert result["step_id"] == "select_device"

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"usb_device": "9-9"},
            )
            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["errors"] == {"usb_device": "device_not_found"}


class TestConfigFlowBT:
    """BT config flow — scan, select, verify, create."""

    async def test_bt_single_device_auto_select(self, hass: HomeAssistant) -> None:
        """Single BT device → auto-skip select → verify → create entry."""
        with (
            patch(
                "custom_components.paperang.config_flow._scan_bt_devices",
                return_value=FAKE_BT_DEVICES[:1],
            ),
            patch(
                "custom_components.paperang.config_flow._verify_bt_printer",
                return_value=True,
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "classic_bluetooth"}
            )

            # Single BT device goes straight to verify → create
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert "Paperang P2" in result["title"]
            assert result["data"][CONF_TRANSPORT] == TRANSPORT_BT
            assert result["data"][CONF_BT_ADDRESS] == "00:15:83:EB:05:17"

    async def test_bt_no_devices_aborts(self, hass: HomeAssistant) -> None:
        """No BT devices found → abort."""
        with patch(
            "custom_components.paperang.config_flow._scan_bt_devices",
            return_value=[],
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "classic_bluetooth"}
            )
            assert result["type"] == data_entry_flow.FlowResultType.ABORT


class TestConfigFlowUser:
    """User-initiated config flow (manual setup)."""

    async def test_user_flow_selects_usb(self, hass: HomeAssistant) -> None:
        """User flow → pick USB → scan → verify → create."""
        with (
            patch(
                "custom_components.paperang.transport.usb.scan_usb_devices",
                return_value=FAKE_USB_DEVICES[:1],
            ),
            patch(
                "custom_components.paperang.transport.usb.verify_printer",
                return_value=True,
            ),
        ):
            # Step 1: user menu → pick USB
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            assert result["type"] == data_entry_flow.FlowResultType.MENU
            assert "usb" in result["menu_options"]

            # Step 2: pick USB → auto-select + verify → create
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"next_step_id": "usb"},
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

    async def test_options_flow_shows_menu(self, hass: HomeAssistant) -> None:
        """Options flow starts with transport menu."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB, CONF_USB_BUS: 1, CONF_USB_PORT: 3},
            version=2,
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        # Options flow shows a form to reconfigure
        assert result["type"] in (
            data_entry_flow.FlowResultType.FORM,
            data_entry_flow.FlowResultType.MENU,
        )

    async def test_duplicate_entry_blocked(self, hass: HomeAssistant) -> None:
        """Second entry with same unique_id is aborted."""
        # Create first entry
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB, CONF_USB_BUS: 1, CONF_USB_PORT: 3},
            unique_id="paperang_usb_1-3",
            version=2,
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        # Try to create a second flow with same unique_id
        with (
            patch(
                "custom_components.paperang.transport.usb.scan_usb_devices",
                return_value=FAKE_USB_DEVICES[:1],
            ),
            patch(
                "custom_components.paperang.transport.usb.verify_printer",
                return_value=True,
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USB}
            )
            # Should abort because unique_id already configured
            assert result["type"] == data_entry_flow.FlowResultType.ABORT
            assert result["reason"] == "already_configured"
