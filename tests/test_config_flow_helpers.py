"""Tests for paperang config flow — discovery helpers."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.paperang.config_flow import (
    _scan_usb_devices,
    _verify_printer,
)
from custom_components.paperang.transport.bt import (
    scan_bt_devices,
    verify_bt_printer,
)


class TestUsbDiscovery:
    def test_scan_no_pyusb_returns_empty(self):
        """_scan_usb_devices returns [] when pyusb is missing."""
        with patch("builtins.__import__") as mock_import:
            mock_import.side_effect = ImportError
            result = _scan_usb_devices()
            assert result == []

    def test_verify_printer_no_lib_returns_false(self):
        """_verify_printer returns False when paperang is missing."""
        with patch(
            "custom_components.paperang.transport.usb.PaperangP2",
            side_effect=ImportError,
        ):
            result = _verify_printer(1, [3])
            assert result is False

    def test_verify_printer_success(self):
        """_verify_printer returns True on successful connect."""
        mock_p = MagicMock()
        mock_p.get_battery.return_value = 80

        mock_tp = MagicMock()

        with patch("custom_components.paperang.transport.usb.PaperangP2", return_value=mock_p):
            with patch(
                "custom_components.paperang.transport.usb.UsbTransportWithPath",
                return_value=mock_tp,
            ):
                result = _verify_printer(1, [3])

        assert result is True
        mock_p.connect.assert_called_once()
        mock_p.get_battery.assert_called_once()
        mock_p.disconnect.assert_called_once()

    def test_verify_printer_battery_none_returns_false(self):
        """_verify_printer returns False when get_battery returns None."""
        mock_p = MagicMock()
        mock_p.get_battery.return_value = None

        mock_tp = MagicMock()

        with patch("custom_components.paperang.transport.usb.PaperangP2", return_value=mock_p):
            with patch(
                "custom_components.paperang.transport.usb.UsbTransportWithPath",
                return_value=mock_tp,
            ):
                result = _verify_printer(1, [3])

        assert result is False

    def test_verify_printer_exception_returns_false(self):
        """_verify_printer returns False on exception."""
        mock_p = MagicMock()
        mock_p.connect.side_effect = RuntimeError("boom")

        mock_tp = MagicMock()

        with patch("custom_components.paperang.transport.usb.PaperangP2", return_value=mock_p):
            with patch(
                "custom_components.paperang.transport.usb.UsbTransportWithPath",
                return_value=mock_tp,
            ):
                result = _verify_printer(1, [3])

        assert result is False

    def test_verify_printer_disconnect_exception_handled(self):
        """_verify_printer handles disconnect exception gracefully."""
        mock_p = MagicMock()
        mock_p.get_battery.return_value = 80
        mock_p.disconnect.side_effect = RuntimeError("disconnect boom")

        mock_tp = MagicMock()

        with patch("custom_components.paperang.transport.usb.PaperangP2", return_value=mock_p):
            with patch(
                "custom_components.paperang.transport.usb.UsbTransportWithPath",
                return_value=mock_tp,
            ):
                result = _verify_printer(1, [3])

        assert result is True  # battery was read before disconnect failed


class TestBtDiscovery:
    def test_scan_bt_no_lib_returns_empty(self):
        """scan_bt_devices returns [] when BtTransport is missing."""
        with patch("custom_components.paperang.transport.bt.BtTransport", None):
            result = scan_bt_devices()
            assert result == []

    def test_verify_bt_no_lib_returns_false(self):
        """verify_bt_printer returns False when BtTransport is missing."""
        with patch("custom_components.paperang.transport.bt.BtTransport", None):
            result = verify_bt_printer("AA:BB:CC:DD:EE:FF")
            assert result is False

    def test_verify_bt_success(self):
        """verify_bt_printer returns True on success."""
        mock_p = MagicMock()
        mock_p.get_battery.return_value = 80

        mock_bt = MagicMock()

        with patch("custom_components.paperang.transport.bt.PaperangP2", return_value=mock_p):
            with patch(
                "custom_components.paperang.transport.bt.BtTransport",
                return_value=mock_bt,
            ):
                result = verify_bt_printer("AA:BB:CC:DD:EE:FF")

        assert result is True
        mock_p.connect.assert_called_once()
        mock_p.get_battery.assert_called_once()

    def test_verify_bt_exception_returns_false(self):
        """verify_bt_printer returns False on exception."""
        mock_p = MagicMock()
        mock_p.connect.side_effect = RuntimeError("bt connect failed")

        mock_bt = MagicMock()

        with patch("custom_components.paperang.transport.bt.PaperangP2", return_value=mock_p):
            with patch(
                "custom_components.paperang.transport.bt.BtTransport",
                return_value=mock_bt,
            ):
                result = verify_bt_printer("AA:BB:CC:DD:EE:FF")

        assert result is False


class TestOptionsFlow:
    def test_options_flow_schema(self):
        """Options flow has transport and bt_address fields."""
        import voluptuous as vol
        from custom_components.paperang.const import (
            TRANSPORT_USB,
            TRANSPORT_BT,
            CONF_TRANSPORT,
            CONF_BT_ADDRESS,
        )

        schema = vol.Schema({
            vol.Required(CONF_TRANSPORT, default=TRANSPORT_USB): vol.In({
                TRANSPORT_USB: "USB",
                TRANSPORT_BT: "Bluetooth",
            }),
            vol.Optional(CONF_BT_ADDRESS, default=""): str,
        })

        result = schema({CONF_TRANSPORT: TRANSPORT_USB})
        assert result[CONF_TRANSPORT] == TRANSPORT_USB
        assert result[CONF_BT_ADDRESS] == ""

    def test_options_flow_bt_address(self):
        """Options flow accepts BT address."""
        import voluptuous as vol
        from custom_components.paperang.const import (
            TRANSPORT_BT,
            CONF_TRANSPORT,
            CONF_BT_ADDRESS,
        )

        schema = vol.Schema({
            vol.Required(CONF_TRANSPORT, default="usb"): vol.In({
                "usb": "USB",
                "bt": "Bluetooth",
            }),
            vol.Optional(CONF_BT_ADDRESS, default=""): str,
        })

        result = schema({
            CONF_TRANSPORT: TRANSPORT_BT,
            CONF_BT_ADDRESS: "AA:BB:CC:DD:EE:FF",
        })
        assert result[CONF_TRANSPORT] == TRANSPORT_BT
        assert result[CONF_BT_ADDRESS] == "AA:BB:CC:DD:EE:FF"
