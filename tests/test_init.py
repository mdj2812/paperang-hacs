"""Tests for paperang __init__.py — factory functions, helpers, migration."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import custom_components.paperang as _mod  # noqa: E402 — needs paperang stubs


@pytest.fixture(autouse=True)
def _clear_transport():
    """Reset transport config after each test to avoid cross-test leakage."""
    _mod._transport_config.clear()
    yield
    _mod._transport_config.clear()


class TestGetPrinter:
    def test_usb_creates_printer_without_transport(self):
        mod = _mod

        mod._transport_config = {"transport": "usb"}

        with patch.object(mod, "PaperangP2") as mock_p2:
            mod._get_printer()
            mock_p2.assert_called_once()
            assert mock_p2.call_args[1] == {}

    def test_ble_with_address(self):
        mod = _mod

        mod._transport_config = {"transport": "ble", "ble_address": "AA:BB:CC:DD:EE:FF"}

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
        mod = _mod

        mod._transport_config = {"transport": "ble"}

        with (
            patch.object(mod, "BleTransport", create=True) as mock_ble_cls,
            patch.object(mod, "PaperangP2") as mock_p2,
        ):
            mock_ble = MagicMock()
            mock_ble_cls.return_value = mock_ble
            mod._get_printer()
            mock_ble_cls.assert_called_once_with()
            mock_p2.assert_called_once_with(transport=mock_ble)

    def test_no_transport_config_defaults_to_usb(self):
        mod = _mod

        mod._transport_config = {}

        with patch.object(mod, "PaperangP2") as mock_p2:
            mod._get_printer()
            mock_p2.assert_called_once()
            assert mock_p2.call_args[1] == {}

    def test_ble_not_installed_falls_back_to_usb(self):
        mod = _mod

        mod._transport_config = {"transport": "ble"}
        mod.BleTransport = None

        class FakePrinter:
            pass

        mod.PaperangP2 = FakePrinter
        result = mod._get_printer()
        assert isinstance(result, FakePrinter)


class TestWithPrinter:
    def test_calls_fn_and_disconnects(self):
        mod = _mod

        mock_printer = MagicMock()

        with patch.object(mod, "_get_printer", return_value=mock_printer):
            result = mod._with_printer(lambda p: "result")
            assert result == "result"
            mock_printer.connect.assert_called_once()
            mock_printer.disconnect.assert_called_once()

    def test_disconnects_on_exception(self):
        mod = _mod

        mock_printer = MagicMock()

        with patch.object(mod, "_get_printer", return_value=mock_printer):
            with pytest.raises(ValueError, match="boom"):
                mod._with_printer(lambda p: (_ for _ in ()).throw(ValueError("boom")))
            mock_printer.connect.assert_called_once()
            mock_printer.disconnect.assert_called_once()

    def test_returns_fn_result(self):
        mod = _mod

        mock_printer = MagicMock()

        with patch.object(mod, "_get_printer", return_value=mock_printer):
            assert mod._with_printer(lambda p: 42) == 42


class TestDoFunctions:
    def test_do_print_text_uses_with_printer(self):
        mod = _mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_print_text("hello", 24, 75)
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_text.assert_called_once_with(
                "hello", font_size=24, heat_density=75
            )

    def test_do_print_qr_uses_with_printer(self):
        mod = _mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_print_qr("https://example.com", 500, 50)
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_qr.assert_called_once_with(
                "https://example.com", heat_density=50, max_width=500
            )

    def test_do_print_pickup_code_uses_with_printer(self):
        mod = _mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_print_pickup_code("19-4308")
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_pickup_code.assert_called_once_with("19-4308")

    def test_do_print_test_page_uses_with_printer(self):
        mod = _mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_print_test_page()
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_test_page.assert_called_once()

    def test_do_feed_paper_uses_with_printer(self):
        mod = _mod

        with patch.object(mod, "_with_printer") as mock_with:
            mod._do_feed_paper(200)
            fn = mock_with.call_args[0][0]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.feed.assert_called_once_with(200)

    def test_do_get_status_success(self):
        mod = _mod

        def fake_with(fn):
            mock_p = MagicMock()
            mock_p.get_battery.return_value = 85
            mock_p.get_status.return_value = "ok"
            return fn(mock_p)

        with patch.object(mod, "_with_printer", side_effect=fake_with):
            result = mod._do_get_status()
            assert result == {"battery": 85, "status": "ok", "available": True}

    def test_do_get_status_failure(self):
        mod = _mod

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


class TestMigrationHandler:
    def test_migrate_v1_to_v2_adds_transport(self):
        from custom_components.paperang.__init__ import async_migrate_entry
        from custom_components.paperang.const import TRANSPORT_USB, CONF_TRANSPORT

        entry = MagicMock()
        entry.version = 1
        entry.data = {}
        hass = MagicMock()

        result = asyncio.run(async_migrate_entry(hass, entry))
        assert result is True
        hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = hass.config_entries.async_update_entry.call_args.kwargs
        assert call_kwargs.get("version") == 2
        assert call_kwargs.get("data") == {CONF_TRANSPORT: TRANSPORT_USB}

    def test_migrate_v2_noop(self):
        from custom_components.paperang.__init__ import async_migrate_entry

        entry = MagicMock()
        entry.version = 2
        entry.data = {"transport": "usb"}
        hass = MagicMock()

        result = asyncio.run(async_migrate_entry(hass, entry))
        assert result is True
        hass.config_entries.async_update_entry.assert_not_called()


class TestServiceHandlers:
    """Test async service handlers via explicit async_setup call."""

    async def test_print_text_service(self, hass, enable_custom_integrations):
        """print_text service handler calls _do_print_text."""
        mod = _mod

        await mod.async_setup(hass, {})
        with patch.object(mod, "_do_print_text") as mock_fn:
            await hass.services.async_call(
                mod.DOMAIN,
                mod.SERVICE_PRINT_TEXT,
                {"text": "hello", "font_size": 24, "heat_density": 75},
                blocking=True,
            )
            mock_fn.assert_called_once_with("hello", 24, 75)

    async def test_print_image_service(self, hass, enable_custom_integrations):
        """print_image service handler calls _do_print_image."""
        mod = _mod

        await mod.async_setup(hass, {})
        mock_profiles = {
            "photo": {"threshold": 100, "brightness": 1.2, "contrast": 0.8}
        }
        with (
            patch.object(mod, "_do_print_image") as mock_fn,
            patch.object(mod, "load_profiles", return_value=mock_profiles),
        ):
            await hass.services.async_call(
                mod.DOMAIN,
                mod.SERVICE_PRINT_IMAGE,
                {"image_url": "http://img", "heat_density": 80, "profile": "photo"},
                blocking=True,
            )
            mock_fn.assert_called_once_with("http://img", 80, 100, 1.2, 0.8)

    async def test_print_image_service_no_profile(
        self, hass, enable_custom_integrations
    ):
        """print_image service without profile uses defaults."""
        mod = _mod

        await mod.async_setup(hass, {})
        with (
            patch.object(mod, "_do_print_image") as mock_fn,
            patch.object(mod, "load_profiles", return_value={}),
        ):
            await hass.services.async_call(
                mod.DOMAIN,
                mod.SERVICE_PRINT_IMAGE,
                {"image_url": "http://img"},
                blocking=True,
            )
            mock_fn.assert_called_once_with("http://img", 75, 128, 1.0, 1.0)

    async def test_print_qr_service(self, hass, enable_custom_integrations):
        """print_qr service handler calls _do_print_qr."""
        mod = _mod

        await mod.async_setup(hass, {})
        with patch.object(mod, "_do_print_qr") as mock_fn:
            await hass.services.async_call(
                mod.DOMAIN,
                mod.SERVICE_PRINT_QR,
                {"qr_content": "https://x.com", "qr_size": 400, "heat_density": 60},
                blocking=True,
            )
            mock_fn.assert_called_once_with("https://x.com", 400, 60)

    async def test_print_pickup_code_service(self, hass, enable_custom_integrations):
        """print_pickup_code service handler calls _do_print_pickup_code."""
        mod = _mod

        await mod.async_setup(hass, {})
        with patch.object(mod, "_do_print_pickup_code") as mock_fn:
            await hass.services.async_call(
                mod.DOMAIN,
                mod.SERVICE_PRINT_PICKUP_CODE,
                {"pickup_code": "19-4308"},
                blocking=True,
            )
            mock_fn.assert_called_once_with("19-4308")

    async def test_get_status_service(self, hass, enable_custom_integrations):
        """get_status service handler calls _do_get_status."""
        mod = _mod

        await mod.async_setup(hass, {})
        with patch.object(
            mod, "_do_get_status", return_value={"battery": 100}
        ) as mock_fn:
            await hass.services.async_call(
                mod.DOMAIN,
                mod.SERVICE_GET_STATUS,
                {},
                blocking=True,
            )
            mock_fn.assert_called_once()

    async def test_feed_paper_service(self, hass, enable_custom_integrations):
        """feed_paper service handler calls _do_feed_paper."""
        mod = _mod

        await mod.async_setup(hass, {})
        with patch.object(mod, "_do_feed_paper") as mock_fn:
            await hass.services.async_call(
                mod.DOMAIN,
                mod.SERVICE_FEED_PAPER,
                {"lines": 10},
                blocking=True,
            )
            mock_fn.assert_called_once_with(10)

    async def test_print_test_page_service(self, hass, enable_custom_integrations):
        """print_test_page service handler calls _do_print_test_page."""
        mod = _mod

        await mod.async_setup(hass, {})
        with patch.object(mod, "_do_print_test_page") as mock_fn:
            await hass.services.async_call(
                mod.DOMAIN,
                mod.SERVICE_PRINT_TEST_PAGE,
                {},
                blocking=True,
            )
            mock_fn.assert_called_once()


class TestReadPrinterState:
    """Test _do_read_printer_state retry/error paths."""

    def test_read_printer_state_all_retries_fail(self):
        """After all retries fail, return {available: False}."""
        mod = _mod

        mock_printer = MagicMock()
        mock_printer.connect.side_effect = RuntimeError("printer offline")

        with patch.object(mod, "_get_printer", return_value=mock_printer):
            result = mod._do_read_printer_state()
            assert result == {"available": False}
            assert mock_printer.connect.call_count == 3
            assert mock_printer.disconnect.call_count == 3

    def test_read_printer_state_single_retry(self):
        """First attempt fails, second succeeds."""
        mod = _mod

        mock_printer = MagicMock()
        mock_printer.connect.side_effect = [
            RuntimeError("attempt 1 fail"),
            None,
        ]
        mock_printer.get_battery.return_value = 80
        mock_printer.get_status.return_value = "ok"

        for reader in mod._STATIC_READERS:
            reader[1](mock_printer)  # just trigger, values don't matter

        with patch.object(mod, "_get_printer", return_value=mock_printer):
            result = mod._do_read_printer_state()
            assert result["available"] is True
            assert result["battery"] == 80
            assert result["status"] == "ok"
            assert mock_printer.connect.call_count == 2
            assert mock_printer.disconnect.call_count == 2
