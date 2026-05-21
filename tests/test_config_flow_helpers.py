"""Tests for paperang config flow — discovery helpers."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.paperang.config_flow import (
    _async_verify_ble_printer,
    _scan_usb_devices,
    _verify_printer,
)
from custom_components.paperang.transport.ble import (
    async_scan_ble_devices as _async_scan_ble_devices,
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


class TestBleDiscovery:
    @pytest.mark.asyncio
    async def test_scan_ble_no_bleak_returns_empty(self):
        """_async_scan_ble_devices returns [] when bleak is missing."""
        with patch("builtins.__import__") as mock_import:
            mock_import.side_effect = ImportError
            result = await _async_scan_ble_devices()
            assert result == []

    @pytest.mark.asyncio
    async def test_scan_ble_returns_paperang_devices(self):
        """_async_scan_ble_devices returns Paperang/MiaoMiaoJi devices."""
        d1 = MagicMock()
        d1.name = "Paperang_P2"
        d1.address = "AA:BB:CC:DD:EE:01"

        d2 = MagicMock()
        d2.name = "MiaoMiaoJi_ABC"
        d2.address = "AA:BB:CC:DD:EE:02"

        d3 = MagicMock()
        d3.name = "Other_Device"
        d3.address = "AA:BB:CC:DD:EE:03"

        async def _mock_discover(timeout=5):
            return [d1, d2, d3]

        with patch("bleak.BleakScanner") as mock_cls:
            mock_cls.discover = _mock_discover
            result = await _async_scan_ble_devices()

        assert len(result) == 2
        assert result[0]["name"] == "Paperang_P2"
        assert result[0]["address"] == "AA:BB:CC:DD:EE:01"
        assert result[1]["name"] == "MiaoMiaoJi_ABC"

    @pytest.mark.asyncio
    async def test_scan_ble_exception_returns_empty(self):
        """_async_scan_ble_devices returns [] on exception."""
        async def _mock_discover_fail(timeout=5):
            raise RuntimeError("scan failed")

        with patch("bleak.BleakScanner") as mock_cls:
            mock_cls.discover = _mock_discover_fail
            result = await _async_scan_ble_devices()

        assert result == []

    @pytest.mark.asyncio
    async def test_verify_ble_no_lib_returns_false(self):
        """_async_verify_ble_printer returns False when paperang is missing."""
        with patch("custom_components.paperang.transport.ble.BleTransport", None):
            result = await _async_verify_ble_printer("AA:BB:CC:DD:EE:FF")
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_ble_success(self):
        """_async_verify_ble_printer returns True on success."""
        mock_p = MagicMock()
        mock_p.get_battery.return_value = 80

        mock_ble = MagicMock()

        with patch("custom_components.paperang.transport.ble.PaperangP2", return_value=mock_p):
            with patch(
                "custom_components.paperang.transport.ble.BleTransport",
                return_value=mock_ble,
            ):
                result = await _async_verify_ble_printer("AA:BB:CC:DD:EE:FF")

        assert result is True
        mock_p.connect.assert_called_once()
        mock_p.get_battery.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_ble_exception_returns_false(self):
        """_async_verify_ble_printer returns False on exception."""
        mock_p = MagicMock()
        mock_p.connect.side_effect = RuntimeError("ble connect failed")

        mock_ble = MagicMock()

        with patch("custom_components.paperang.transport.ble.PaperangP2", return_value=mock_p):
            with patch(
                "custom_components.paperang.transport.ble.BleTransport",
                return_value=mock_ble,
            ):
                result = await _async_verify_ble_printer("AA:BB:CC:DD:EE:FF")

        assert result is False


class TestOptionsFlow:
    def test_options_flow_schema(self):
        """Options flow has transport and ble_address fields."""
        import voluptuous as vol
        from custom_components.paperang.const import (
            TRANSPORT_USB,
            TRANSPORT_BLE,
            CONF_TRANSPORT,
            CONF_BLE_ADDRESS,
        )

        schema = vol.Schema({
            vol.Required(CONF_TRANSPORT, default=TRANSPORT_USB): vol.In({
                TRANSPORT_USB: "USB",
                TRANSPORT_BLE: "Bluetooth BLE",
            }),
            vol.Optional(CONF_BLE_ADDRESS, default=""): str,
        })

        result = schema({CONF_TRANSPORT: TRANSPORT_USB})
        assert result[CONF_TRANSPORT] == TRANSPORT_USB
        assert result[CONF_BLE_ADDRESS] == ""

    def test_options_flow_ble_address(self):
        """Options flow accepts BLE address."""
        import voluptuous as vol
        from custom_components.paperang.const import (
            TRANSPORT_BLE,
            CONF_TRANSPORT,
            CONF_BLE_ADDRESS,
        )

        schema = vol.Schema({
            vol.Required(CONF_TRANSPORT, default="usb"): vol.In({
                "usb": "USB",
                "ble": "Bluetooth BLE",
            }),
            vol.Optional(CONF_BLE_ADDRESS, default=""): str,
        })

        result = schema({
            CONF_TRANSPORT: TRANSPORT_BLE,
            CONF_BLE_ADDRESS: "AA:BB:CC:DD:EE:FF",
        })
        assert result[CONF_TRANSPORT] == TRANSPORT_BLE
        assert result[CONF_BLE_ADDRESS] == "AA:BB:CC:DD:EE:FF"
