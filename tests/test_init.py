"""Tests for paperang __init__.py — factory functions and helpers."""
from unittest.mock import MagicMock, patch

import pytest


class TestGetPrinter:
    def test_usb_creates_printer_without_transport(self):
        """USB transport: PaperangP2() with no transport arg."""
        from custom_components.paperang import __init__ as mod

        # Simulate USB config
        mod._transport_config = {"transport": "usb"}

        with patch.object(mod, "PaperangP2") as mock_p2:
            mod._get_printer()
            mock_p2.assert_called_once()
            # Should be called with no transport arg (uses default USB)
            assert mock_p2.call_args[1] == {}

    def test_ble_with_address(self):
        """BLE with explicit MAC address."""
        from custom_components.paperang import __init__ as mod

        mod._transport_config = {
            "transport": "ble",
            "ble_address": "AA:BB:CC:DD:EE:FF",
        }

        with (
            patch.object(mod, "BleTransport", create=True) as mock_ble_cls,
            patch.object(mod, "PaperangP2") as mock_p2,
        ):
            mock_ble = MagicMock()
            mock_ble_cls.return_value = mock_ble
            mod._get_printer()
            mock_ble_cls.assert_called_once_with(address="AA:BB:CC:DD:EE:FF")
            mock_p2.assert_called_once_with(transport=mock_ble)

    def test_ble_without_address(self):
        """BLE without MAC → auto-scan."""
        from custom_components.paperang import __init__ as mod

        mod._transport_config = {"transport": "ble"}

        with (
            patch.object(mod, "BleTransport", create=True) as mock_ble_cls,
            patch.object(mod, "PaperangP2") as mock_p2,
        ):
            mock_ble = MagicMock()
            mock_ble_cls.return_value = mock_ble
            mod._get_printer()
            mock_ble_cls.assert_called_once_with()  # no args = auto-scan
            mock_p2.assert_called_once_with(transport=mock_ble)

    def test_no_transport_config_defaults_to_usb(self):
        """Empty config → USB."""
        from custom_components.paperang import __init__ as mod

        mod._transport_config = {}

        with patch.object(mod, "PaperangP2") as mock_p2:
            mod._get_printer()
            mock_p2.assert_called_once()
            assert mock_p2.call_args[1] == {}

    def test_ble_not_installed_falls_back_to_usb(self):
        """When BleTransport is None, fall back to USB."""
        from custom_components.paperang import __init__ as mod

        mod._transport_config = {"transport": "ble"}
        mod.BleTransport = None  # simulate no bleak

        class FakePrinter:
            pass

        mod.PaperangP2 = FakePrinter
        result = mod._get_printer()
        assert isinstance(result, FakePrinter)
        # Should not have transport kwarg since BleTransport is None
        assert mod._transport_config == {"transport": "ble"}


class TestWithPrinter:
    def test_calls_fn_and_disconnects(self):
        """_with_printer: connect → fn(printer) → disconnect."""
        from custom_components.paperang import __init__ as mod

        mock_printer = MagicMock()
        mock_printer.connect = MagicMock()
        mock_printer.disconnect = MagicMock()

        with patch.object(mod, "_get_printer", return_value=mock_printer):
            result = mod._with_printer(lambda p: "result")
            assert result == "result"
            mock_printer.connect.assert_called_once()
            mock_printer.disconnect.assert_called_once()

    def test_disconnects_on_exception(self):
        """_with_printer: disconnect always called, even on error."""
        from custom_components.paperang import __init__ as mod

        mock_printer = MagicMock()
        mock_printer.connect = MagicMock()
        mock_printer.disconnect = MagicMock()

        with patch.object(mod, "_get_printer", return_value=mock_printer):
            with pytest.raises(ValueError, match="boom"):
                mod._with_printer(lambda p: (_ for _ in ()).throw(ValueError("boom")))
            mock_printer.connect.assert_called_once()
            mock_printer.disconnect.assert_called_once()

    def test_returns_fn_result(self):
        """_with_printer returns whatever fn returns."""
        from custom_components.paperang import __init__ as mod

        mock_printer = MagicMock()
        mock_printer.connect = MagicMock()
        mock_printer.disconnect = MagicMock()

        with patch.object(mod, "_get_printer", return_value=mock_printer):
            result = mod._with_printer(lambda p: 42)
            assert result == 42


class TestDoFunctions:
    def test_do_print_text_uses_with_printer(self):
        from custom_components.paperang import __init__ as mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_print_text("hello", 24, 75)
            mock_with.assert_called_once()
            # Call the lambda to verify it calls correct method
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_text.assert_called_once_with("hello", font_size=24, heat_density=75)

    def test_do_print_qr_uses_with_printer(self):
        from custom_components.paperang import __init__ as mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_print_qr("https://example.com", 500, 50)
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_qr.assert_called_once_with(
                "https://example.com", heat_density=50, max_width=500
            )

    def test_do_print_pickup_code_uses_with_printer(self):
        from custom_components.paperang import __init__ as mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_print_pickup_code("19-4308")
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_pickup_code.assert_called_once_with("19-4308")

    def test_do_print_test_page_uses_with_printer(self):
        from custom_components.paperang import __init__ as mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_print_test_page()
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_test_page.assert_called_once()

    def test_do_feed_paper_uses_with_printer(self):
        from custom_components.paperang import __init__ as mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_feed_paper(200)
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.feed.assert_called_once_with(200)

    def test_do_get_status_success(self):
        from custom_components.paperang import __init__ as mod

        def fake_with(fn):
            mock_p = MagicMock()
            mock_p.get_battery.return_value = 85
            mock_p.get_status.return_value = "ok"
            return fn(mock_p)

        with patch.object(mod, "_with_printer", side_effect=fake_with):
            result = mod._do_get_status()
            assert result == {"battery": 85, "status": "ok", "available": True}

    def test_do_get_status_failure(self):
        from custom_components.paperang import __init__ as mod

        def fake_with(fn):
            raise RuntimeError("printer offline")

        with patch.object(mod, "_with_printer", side_effect=fake_with):
            result = mod._do_get_status()
            assert result == {
                "battery": None,
                "status": None,
                "available": False,
                "error": "printer offline",
            }
