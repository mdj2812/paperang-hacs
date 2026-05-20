"""Tests for paperang config flow — discovery helpers."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.paperang.config_flow import (
    _scan_usb_devices,
    _verify_printer,
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
        with patch.dict("sys.modules", {"paperang": None}):
            original = __import__

            def _fake_import(name, *args, **kwargs):
                if name == "paperang":
                    raise ImportError
                return original(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=_fake_import):
                result = _verify_printer(1, [3])
                assert result is False

    def test_verify_printer_success(self):
        """_verify_printer returns True on successful connect."""
        mock_p = MagicMock()
        mock_p.get_battery.return_value = 80

        mock_tp = MagicMock()

        with patch("paperang.PaperangP2", return_value=mock_p):
            with patch("custom_components.paperang.UsbTransportWithPath", return_value=mock_tp):
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

        with patch("paperang.PaperangP2", return_value=mock_p):
            with patch("custom_components.paperang.UsbTransportWithPath", return_value=mock_tp):
                result = _verify_printer(1, [3])

        assert result is False

    def test_verify_printer_exception_returns_false(self):
        """_verify_printer returns False on exception."""
        mock_p = MagicMock()
        mock_p.connect.side_effect = RuntimeError("boom")

        mock_tp = MagicMock()

        with patch("paperang.PaperangP2", return_value=mock_p):
            with patch("custom_components.paperang.UsbTransportWithPath", return_value=mock_tp):
                result = _verify_printer(1, [3])

        assert result is False
