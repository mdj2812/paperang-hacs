"""Tests for USB transport layer — connect() tested via integration layer."""

from unittest.mock import MagicMock, patch

import pytest


def _check_usb():
    """Check if pyusb is available."""
    try:
        import usb.core  # noqa: F401
        return True
    except ImportError:
        return False


_usb_available = _check_usb()


class TestUsbTransportWithPath:
    """Tests for UsbTransportWithPath constructor."""

    def test_init_stores_attrs(self):
        """Constructor stores bus, port, and initializes device handles to None."""
        from custom_components.paperang.transport.usb import UsbTransportWithPath

        t = UsbTransportWithPath(bus=2, port=[1, 3])
        assert t._target_bus == 2
        assert t._target_port == (1, 3)
        assert t._dev is None
        assert t._ep_out is None
        assert t._ep_in is None

    def test_init_empty_port(self):
        """Empty port list results in empty tuple."""
        from custom_components.paperang.transport.usb import UsbTransportWithPath

        t = UsbTransportWithPath(bus=1, port=[])
        assert t._target_port == ()


class TestScanUsbDevices:
    """Tests for scan_usb_devices()."""

    @pytest.mark.skipif(not _usb_available, reason="pyusb not installed")
    def test_returns_devices(self):
        """Returns list of device dicts when devices are found."""
        from custom_components.paperang.transport.usb import scan_usb_devices

        dev = MagicMock()
        dev.bus = 2
        dev.port_numbers = [1, 3]
        dev.address = 5

        with patch("usb.core.find", return_value=[dev]):
            result = scan_usb_devices()

        assert len(result) == 1
        assert result[0] == {
            "usb_path": "2-1-3", "bus": 2, "port": [1, 3], "address": 5,
        }

    @pytest.mark.skipif(not _usb_available, reason="pyusb not installed")
    def test_returns_empty(self):
        """Returns empty list when no devices found."""
        from custom_components.paperang.transport.usb import scan_usb_devices

        with patch("usb.core.find", return_value=[]):
            result = scan_usb_devices()
        assert result == []

    @pytest.mark.skipif(not _usb_available, reason="pyusb not installed")
    def test_device_none_port_numbers(self):
        """Device with None port_numbers falls back to empty list."""
        from custom_components.paperang.transport.usb import scan_usb_devices

        dev = MagicMock()
        dev.bus = 1
        dev.port_numbers = None
        dev.address = 3

        with patch("usb.core.find", return_value=[dev]):
            result = scan_usb_devices()

        assert result[0]["usb_path"] == "1"
        assert result[0]["port"] == []


class TestVerifyPrinter:
    """Tests for verify_printer()."""

    def test_verify_success(self):
        """Returns True on successful connect and battery read."""
        from custom_components.paperang.transport.usb import verify_printer

        mock_printer = MagicMock()
        mock_printer.get_battery.return_value = 80

        with patch(
            "custom_components.paperang.transport.usb.PaperangP2",
            return_value=mock_printer,
        ), patch(
            "custom_components.paperang.transport.usb.UsbTransportWithPath"
        ):
            result = verify_printer(bus=1, port=[3])

        assert result is True
        mock_printer.connect.assert_called_once()
        mock_printer.get_battery.assert_called_once()
        mock_printer.disconnect.assert_called_once()

    def test_verify_battery_none(self):
        """Returns False when get_battery returns None."""
        from custom_components.paperang.transport.usb import verify_printer

        mock_printer = MagicMock()
        mock_printer.get_battery.return_value = None

        with patch(
            "custom_components.paperang.transport.usb.PaperangP2",
            return_value=mock_printer,
        ), patch(
            "custom_components.paperang.transport.usb.UsbTransportWithPath"
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is False

    def test_verify_exception(self):
        """Returns False on exception."""
        from custom_components.paperang.transport.usb import verify_printer

        mock_printer = MagicMock()
        mock_printer.connect.side_effect = RuntimeError("boom")

        with patch(
            "custom_components.paperang.transport.usb.PaperangP2",
            return_value=mock_printer,
        ), patch(
            "custom_components.paperang.transport.usb.UsbTransportWithPath"
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is False

    def test_verify_disconnect_error_handled(self):
        """Disconnect exception after success is swallowed."""
        from custom_components.paperang.transport.usb import verify_printer

        mock_printer = MagicMock()
        mock_printer.get_battery.return_value = 80
        mock_printer.disconnect.side_effect = RuntimeError("fail")

        with patch(
            "custom_components.paperang.transport.usb.PaperangP2",
            return_value=mock_printer,
        ), patch(
            "custom_components.paperang.transport.usb.UsbTransportWithPath"
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is True

    def test_verify_connect_oserror(self):
        """OSError during connect is caught."""
        from custom_components.paperang.transport.usb import verify_printer

        mock_printer = MagicMock()
        mock_printer.connect.side_effect = OSError("port error")

        with patch(
            "custom_components.paperang.transport.usb.PaperangP2",
            return_value=mock_printer,
        ), patch(
            "custom_components.paperang.transport.usb.UsbTransportWithPath"
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is False
