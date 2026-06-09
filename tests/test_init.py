"""Tests for paperang __init__.py — factory functions, helpers, migration."""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

FAKE_ENTRY_ID = "test_entry_123"


class TestGetPrinter:
    def test_usb_creates_printer_without_specific_bus_port(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as pr

        mod._transport_configs[FAKE_ENTRY_ID] = {"transport": "usb"}

        with patch.object(pr, "PaperangP2") as mock_p2:
            mod._get_printer(FAKE_ENTRY_ID)
            mock_p2.assert_called_once()
            assert mock_p2.call_args[1] == {}

    def test_usb_with_bus_port_uses_custom_transport(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as pr

        mod._transport_configs[FAKE_ENTRY_ID] = {
            "transport": "usb", "usb_bus": 1, "usb_port": [3],
        }

        with (
            patch.object(pr, "UsbTransportWithPath") as mock_tp,
            patch.object(pr, "PaperangP2") as mock_p2,
        ):
            mock_transport = MagicMock()
            mock_tp.return_value = mock_transport
            mod._get_printer(FAKE_ENTRY_ID)
            mock_tp.assert_called_once_with(bus=1, port=[3])
            mock_p2.assert_called_once_with(transport=mock_transport)

    def test_no_transport_configs_falls_back_to_usb(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as pr

        mod._transport_configs.clear()

        with patch.object(pr, "PaperangP2") as mock_p2:
            mod._get_printer()
            mock_p2.assert_called_once()

    def test_entry_id_not_found_uses_first_configured(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as pr

        mod._transport_configs.clear()
        mod._transport_configs[FAKE_ENTRY_ID] = {"transport": "usb"}

        with patch.object(pr, "PaperangP2") as mock_p2:
            mod._get_printer("nonexistent")
            mock_p2.assert_called_once()


class TestWithPrinter:
    def test_calls_fn_and_returns_result(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as rt

        mock_printer = MagicMock()

        with patch.object(rt, "_get_or_reuse_printer", return_value=mock_printer):
            result = mod._with_printer(FAKE_ENTRY_ID, lambda p: "result")
            assert result == "result"

    def test_exception_pops_cache_and_propagates(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as rt

        mock_printer = MagicMock()

        with (
            patch.object(rt, "_get_or_reuse_printer", return_value=mock_printer),
            patch.object(rt, "_pop_printer") as mock_pop,
        ):
            with pytest.raises(ValueError, match="boom"):
                mod._with_printer(
                    FAKE_ENTRY_ID,
                    lambda p: (_ for _ in ()).throw(ValueError("boom")),
                )
            mock_pop.assert_called_once_with(FAKE_ENTRY_ID)

    def test_returns_fn_result(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as rt

        mock_printer = MagicMock()

        with patch.object(rt, "_get_or_reuse_printer", return_value=mock_printer):
            assert mod._with_printer(FAKE_ENTRY_ID, lambda p: 42) == 42


class TestDoFunctions:
    def test_do_print_text_uses_with_printer(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.blocking as pb

        with patch.object(pb, "_with_printer") as mock_with:
            mod._do_print_text(FAKE_ENTRY_ID, "hello", 24, 75)
            assert mock_with.call_args[0][0] == FAKE_ENTRY_ID
            fn = mock_with.call_args[0][1]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_text.assert_called_once_with("hello", font_size=24, heat_density=75)

    def test_do_print_qr_uses_with_printer(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.blocking as pb

        with patch.object(pb, "_with_printer") as mock_with:
            mod._do_print_qr(FAKE_ENTRY_ID, "https://example.com", 500, 50)
            assert mock_with.call_args[0][0] == FAKE_ENTRY_ID
            fn = mock_with.call_args[0][1]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_qr.assert_called_once_with("https://example.com", heat_density=50, max_width=500)

    def test_do_print_pickup_code_uses_with_printer(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.blocking as pb

        with patch.object(pb, "_with_printer") as mock_with:
            mod._do_print_pickup_code(FAKE_ENTRY_ID, "19-4308")
            assert mock_with.call_args[0][0] == FAKE_ENTRY_ID
            fn = mock_with.call_args[0][1]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_pickup_code.assert_called_once_with("19-4308")

    def test_do_print_test_page_uses_with_printer(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.blocking as pb

        with patch.object(pb, "_with_printer") as mock_with:
            mod._do_print_test_page(FAKE_ENTRY_ID)
            assert mock_with.call_args[0][0] == FAKE_ENTRY_ID
            fn = mock_with.call_args[0][1]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.print_test_page.assert_called_once()

    def test_do_feed_paper_uses_with_printer(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.blocking as pb

        with patch.object(pb, "_with_printer") as mock_with:
            mod._do_feed_paper(FAKE_ENTRY_ID, 200)
            assert mock_with.call_args[0][0] == FAKE_ENTRY_ID
            fn = mock_with.call_args[0][1]
            mock_p = MagicMock()
            fn(mock_p)
            mock_p.feed.assert_called_once_with(200)

    def test_do_get_status_success(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.blocking as pb

        def fake_with(entry_id, fn):
            mock_p = MagicMock()
            mock_p.get_battery.return_value = 85
            mock_p.get_status.return_value = "ok"
            return fn(mock_p)

        with patch.object(pb, "_with_printer", side_effect=fake_with):
            result = mod._do_get_status(FAKE_ENTRY_ID)
            assert result == {"battery": 85, "status": "ok", "available": True}

    def test_do_get_status_failure(self):
        import custom_components.paperang as mod
        import custom_components.paperang.core.blocking as pb

        def fake_with(entry_id, fn):
            raise RuntimeError("printer offline")

        with patch.object(pb, "_with_printer", side_effect=fake_with):
            result = mod._do_get_status(FAKE_ENTRY_ID)
            assert result == {"battery": None, "status": None, "available": False, "error": "printer offline"}


class TestUsbTransportWithPath:
    def test_init_stores_target_bus_port(self):
        from custom_components.paperang import UsbTransportWithPath

        transport = UsbTransportWithPath(bus=2, port=[1, 3], vid=0x4348, pid=0x5584)
        assert transport._target_bus == 2
        assert transport._target_port == (1, 3)


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
