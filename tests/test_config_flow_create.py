"""Tests for paperang config flow — success/entry creation paths."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.paperang.config_flow import PaperangConfigFlow

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _make_flow(hass, unique_id=None):
    """Create a flow with minimal mocked HA context."""
    flow = PaperangConfigFlow()
    flow.hass = hass
    flow._async_current_entries = MagicMock(return_value=[])

    # Mock the HA config flow internals needed for async_create_entry
    flow.handler = "paperang"
    flow.context = {"source": "user"}

    return flow


class TestConfigFlowCreateEntry:
    @pytest.mark.asyncio
    async def test_usb_verify_success_creates_entry(self, hass: HomeAssistant) -> None:
        """USB verify step creates entry on successful communication."""
        flow = _make_flow(hass)
        flow._selected_usb = {"usb_path": "1-3", "bus": 1, "port": [3]}

        with patch(
            "custom_components.paperang.config_flow._verify_printer",
            return_value=True,
        ):
            result = await flow.async_step_usb_verify()

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert "Paperang P2 (USB 1-3)" in result["title"]
        assert result["data"]["transport"] == "usb"
        assert result["data"]["usb_bus"] == 1
        assert result["data"]["usb_port"] == [3]

    @pytest.mark.asyncio
    async def test_bt_verify_success_creates_entry(self, hass: HomeAssistant) -> None:
        """BT verify step creates entry on successful communication."""
        flow = _make_flow(hass)
        flow._selected_bt = {
            "name": "Paperang_P2",
            "address": "AA:BB:CC:DD:EE:FF",
        }

        with patch(
            "custom_components.paperang.config_flow._verify_bt_printer",
            return_value=True,
        ):
            result = await flow.async_step_bt_verify()

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert "Paperang_P2" in result["title"]
        assert result["data"]["transport"] == "bt"
        assert result["data"]["bt_address"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_user_step_usb_single_device_creates_entry(
        self, hass: HomeAssistant
    ) -> None:
        """User step with USB and single device creates entry."""
        flow = _make_flow(hass)

        device = {"usb_path": "1-3", "bus": 1, "port": [3], "address": 5}

        with patch(
            "custom_components.paperang.config_flow._scan_usb_devices",
            return_value=[device],
        ):
            with patch(
                "custom_components.paperang.config_flow._verify_printer",
                return_value=True,
            ):
                result = await flow.async_step_user({"transport": "usb"})

        assert result["type"] == FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_user_step_bt_no_devices_shows_error(
        self, hass: HomeAssistant
    ) -> None:
        """User step with BT triggers scan; no devices returns error."""
        flow = _make_flow(hass)
        result = await flow.async_step_user({"transport": "bt"})
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "no_bt_device_found"

    @pytest.mark.asyncio
    async def test_select_bt_device_form(self, hass: HomeAssistant) -> None:
        """Select BT device step shows dropdown."""
        flow = _make_flow(hass)
        flow._bt_discovered = [
            {"name": "Paperang_P2", "address": "AA:BB:CC:DD:EE:01"},
            {"name": "MiaoMiaoJi", "address": "AA:BB:CC:DD:EE:02"},
        ]

        result = await flow.async_step_select_bt_device()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select_bt_device"

    @pytest.mark.asyncio
    async def test_select_bt_device_submit_goes_to_verify(
        self, hass: HomeAssistant
    ) -> None:
        """Select BT device submit triggers verify."""
        flow = _make_flow(hass)
        flow._bt_discovered = [
            {"name": "Paperang_P2", "address": "AA:BB:CC:DD:EE:01"},
        ]

        with patch(
            "custom_components.paperang.config_flow._verify_bt_printer",
            return_value=True,
        ):
            result = await flow.async_step_select_bt_device(
                {"bt_device": "AA:BB:CC:DD:EE:01"}
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_select_usb_device_invalid_selection(
        self, hass: HomeAssistant
    ) -> None:
        """Select USB device with invalid path shows error."""
        flow = _make_flow(hass)
        flow._usb_discovered = [
            {"usb_path": "1-3", "bus": 1, "port": [3], "address": 5},
        ]

        result = await flow.async_step_select_device({"usb_device": "1-999"})

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["usb_device"] == "device_not_found"

    @pytest.mark.asyncio
    async def test_user_step_initial_form(self, hass: HomeAssistant) -> None:
        """User step shows transport selection form."""
        flow = _make_flow(hass)

        result = await flow.async_step_user()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_async_step_import(self, hass: HomeAssistant) -> None:
        """Import step delegates to user step."""
        flow = _make_flow(hass)

        result = await flow.async_step_import()
        assert result["type"] == FlowResultType.FORM
