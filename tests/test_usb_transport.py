"""Tests for USB transport layer — connect() tested via integration layer."""

from unittest.mock import MagicMock, patch

import pytest


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
            "usb_path": "2-1-3",
            "bus": 2,
            "port": [1, 3],
            "address": 5,
        }

    def test_returns_empty(self):
        """Returns empty list when no devices found."""
        from custom_components.paperang.transport.usb import scan_usb_devices

        with patch("usb.core.find", return_value=[]):
            result = scan_usb_devices()
        assert result == []

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

        with (
            patch(
                "custom_components.paperang.transport.usb.PaperangP2",
                return_value=mock_printer,
            ),
            patch("custom_components.paperang.transport.usb.UsbTransportWithPath"),
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

        with (
            patch(
                "custom_components.paperang.transport.usb.PaperangP2",
                return_value=mock_printer,
            ),
            patch("custom_components.paperang.transport.usb.UsbTransportWithPath"),
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is False

    def test_verify_exception(self):
        """Returns False on exception."""
        from custom_components.paperang.transport.usb import verify_printer

        mock_printer = MagicMock()
        mock_printer.connect.side_effect = RuntimeError("boom")

        with (
            patch(
                "custom_components.paperang.transport.usb.PaperangP2",
                return_value=mock_printer,
            ),
            patch("custom_components.paperang.transport.usb.UsbTransportWithPath"),
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is False

    def test_verify_disconnect_error_handled(self):
        """Disconnect exception after success is swallowed."""
        from custom_components.paperang.transport.usb import verify_printer

        mock_printer = MagicMock()
        mock_printer.get_battery.return_value = 80
        mock_printer.disconnect.side_effect = RuntimeError("fail")

        with (
            patch(
                "custom_components.paperang.transport.usb.PaperangP2",
                return_value=mock_printer,
            ),
            patch("custom_components.paperang.transport.usb.UsbTransportWithPath"),
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is True

    def test_verify_connect_oserror(self):
        """OSError during connect is caught."""
        from custom_components.paperang.transport.usb import verify_printer

        mock_printer = MagicMock()
        mock_printer.connect.side_effect = OSError("port error")

        with (
            patch(
                "custom_components.paperang.transport.usb.PaperangP2",
                return_value=mock_printer,
            ),
            patch("custom_components.paperang.transport.usb.UsbTransportWithPath"),
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is False

    def test_verify_resource_busy_retry_succeeds(self):
        """Resource busy on first attempt, succeeds on retry."""
        from custom_components.paperang.transport.usb import verify_printer

        fail_printer = MagicMock()
        fail_printer.connect.side_effect = RuntimeError("Resource busy")

        ok_printer = MagicMock()
        ok_printer.get_battery.return_value = 80

        with (
            patch(
                "custom_components.paperang.transport.usb.PaperangP2",
                side_effect=[fail_printer, ok_printer],
            ),
            patch("custom_components.paperang.transport.usb.UsbTransportWithPath"),
            patch("time.sleep"),  # skip actual sleep
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is True

    def test_verify_resource_busy_exhausted(self):
        """Resource busy ×3 → returns False after all retries exhausted."""
        from custom_components.paperang.transport.usb import verify_printer

        fail_printer = MagicMock()
        fail_printer.connect.side_effect = RuntimeError("Resource busy")

        with (
            patch(
                "custom_components.paperang.transport.usb.PaperangP2",
                return_value=fail_printer,
            ),
            patch("custom_components.paperang.transport.usb.UsbTransportWithPath"),
            patch("time.sleep"),
        ):
            result = verify_printer(bus=1, port=[3])
        assert result is False


class TestScanUsbDevicesImportError:
    """Tests for scan_usb_devices() when pyusb is not installed."""

    def test_returns_empty_on_import_error(self):
        """Returns [] when usb.core cannot be imported."""
        import sys

        # Temporarily remove usb.core from sys.modules so the
        # `import usb.core` inside scan_usb_devices raises ImportError.
        usb_core = sys.modules.pop("usb.core", None)
        try:
            from custom_components.paperang.transport.usb import scan_usb_devices

            result = scan_usb_devices()
            assert result == []
        finally:
            if usb_core is not None:
                sys.modules["usb.core"] = usb_core


class TestUsbTransportConnect:
    """Tests for UsbTransportWithPath.connect() — mocked USB stack."""

    def test_connect_finds_and_configures_device(self):
        """connect() locates device, detaches kernel driver, configures endpoints."""
        from custom_components.paperang.transport.usb import UsbTransportWithPath

        mock_dev = MagicMock()
        mock_dev.bus = 2
        mock_dev.port_numbers = [1, 3]
        mock_dev.is_kernel_driver_active.return_value = True

        mock_cfg = MagicMock()
        mock_intf = MagicMock()
        mock_cfg.__getitem__.return_value = mock_intf
        mock_dev.get_active_configuration.return_value = mock_cfg

        # find_descriptor returns different mocks for OUT and IN
        mock_ep_out = MagicMock()
        mock_ep_in = MagicMock()

        t = UsbTransportWithPath(bus=2, port=[1, 3])

        with (
            patch("usb.core.find", return_value=[mock_dev]),
            patch("usb.util.find_descriptor", side_effect=[mock_ep_out, mock_ep_in]),
        ):
            result = t.connect()

        assert result is True
        assert t._dev is mock_dev
        assert t._ep_out is mock_ep_out
        assert t._ep_in is mock_ep_in
        mock_dev.detach_kernel_driver.assert_called_once_with(0)
        mock_dev.set_configuration.assert_called_once()

    def test_connect_device_not_found_raises(self):
        """RuntimeError when no matching device at specified bus/port."""
        from custom_components.paperang.transport.usb import UsbTransportWithPath

        wrong_dev = MagicMock()
        wrong_dev.bus = 99
        wrong_dev.port_numbers = [9, 9]

        t = UsbTransportWithPath(bus=2, port=[1, 3])

        with patch("usb.core.find", return_value=[wrong_dev]):
            with pytest.raises(
                RuntimeError, match="Paperang P2 not found at bus=2"
            ):
                t.connect()

    def test_connect_no_kernel_driver(self):
        """connect() works when kernel driver is not active."""
        from custom_components.paperang.transport.usb import UsbTransportWithPath

        mock_dev = MagicMock()
        mock_dev.bus = 1
        mock_dev.port_numbers = [4]
        mock_dev.is_kernel_driver_active.return_value = False

        mock_cfg = MagicMock()
        mock_cfg.__getitem__.return_value = MagicMock()
        mock_dev.get_active_configuration.return_value = mock_cfg

        t = UsbTransportWithPath(bus=1, port=[4])

        with (
            patch("usb.core.find", return_value=[mock_dev]),
            patch("usb.util.find_descriptor", side_effect=[MagicMock(), MagicMock()]),
        ):
            result = t.connect()

        assert result is True
        mock_dev.detach_kernel_driver.assert_not_called()
        mock_dev.set_configuration.assert_called_once()
