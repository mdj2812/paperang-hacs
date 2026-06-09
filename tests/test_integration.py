"""Tests for paperang integration — service calls and entry setup."""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import DOMAIN, TRANSPORT_USB, CONF_TRANSPORT

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

_PATCH_RUNTIME_GET = "custom_components.paperang.core.runtime._get_printer"
_PATCH_BLOCK_WITH = "custom_components.paperang.core.blocking._with_printer"


@pytest.fixture
def mock_printer():
    """Return a fully mocked printer."""
    mock_p = MagicMock()
    mock_p.get_battery.return_value = 80
    mock_p.get_status.return_value = "online"
    mock_p.get_voltage.return_value = 4200
    mock_p.get_temperature.return_value = 35
    mock_p.get_heat_density.return_value = 75
    mock_p.get_paper_type.return_value = "normal"
    mock_p.get_version.return_value = "720897"
    mock_p.get_model.return_value = "P2"
    mock_p.get_sn.return_value = "SN123"
    mock_p.get_board_version.return_value = "V1.0"
    mock_p.get_hw_info.return_value = "ABC"
    return mock_p


class TestSetupEntry:
    async def test_setup_entry_stores_transport_config(self, hass: HomeAssistant, mock_printer) -> None:
        """Setup stores per-entry transport config."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod

        with patch(_PATCH_RUNTIME_GET, return_value=mock_printer):
            with patch.object(mod, "async_setup", return_value=True):
                with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=None):
                    result = await mod.async_setup_entry(hass, entry)

        assert result is True
        assert entry.entry_id in mod._transport_configs
        assert entry.entry_id in hass.data[DOMAIN]

    async def test_setup_entry_refreshes_coordinator(self, hass: HomeAssistant, mock_printer) -> None:
        """Setup triggers an initial coordinator refresh."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod

        with patch(_PATCH_RUNTIME_GET, return_value=mock_printer):
            with patch.object(mod, "async_setup", return_value=True):
                with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=None):
                    result = await mod.async_setup_entry(hass, entry)

        assert result is True
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.data is not None
        assert coordinator.data.get("available") is True

    async def test_unload_entry_cleans_up(self, hass: HomeAssistant, mock_printer) -> None:
        """Unload removes coordinator and clears caches."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod

        with patch(_PATCH_RUNTIME_GET, return_value=mock_printer):
            with patch.object(mod, "async_setup", return_value=True):
                with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=None):
                    await mod.async_setup_entry(hass, entry)

        assert entry.entry_id in hass.data[DOMAIN]

        with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
            result = await mod.async_unload_entry(hass, entry)

        assert result is True
        assert entry.entry_id not in hass.data[DOMAIN]


class TestServiceCalls:
    async def test_print_text_service(self, hass: HomeAssistant, mock_printer) -> None:
        """print_text service calls the printer."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod
        mod._transport_configs[entry.entry_id] = dict(entry.data)

        with patch(_PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            # Call the do-function directly
            mod._do_print_text(entry.entry_id, "Hello", 24, 75)

        mock_printer.print_text.assert_called_once_with("Hello", font_size=24, heat_density=75)

    async def test_feed_paper_service(self, hass: HomeAssistant, mock_printer) -> None:
        """feed_paper service calls the printer."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod
        mod._transport_configs[entry.entry_id] = dict(entry.data)

        with patch(_PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_feed_paper(entry.entry_id, 100)

        mock_printer.feed.assert_called_once_with(100)

    async def test_print_test_page_service(self, hass: HomeAssistant, mock_printer) -> None:
        """print_test_page service calls the printer."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod
        mod._transport_configs[entry.entry_id] = dict(entry.data)

        with patch(_PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_test_page(entry.entry_id)

        mock_printer.print_test_page.assert_called_once()

    async def test_do_get_status(self, hass: HomeAssistant, mock_printer) -> None:
        """_do_get_status returns correct dict."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod
        mod._transport_configs[entry.entry_id] = dict(entry.data)

        with patch(_PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            result = mod._do_get_status(entry.entry_id)

        assert result == {"battery": 80, "status": "online", "available": True}

    async def test_get_printer_usb_with_path(self) -> None:
        """_get_printer with USB bus/port uses UsbTransportWithPath."""
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as pr

        mod._transport_configs.clear()
        mod._transport_configs["test_eid"] = {
            "transport": "usb", "usb_bus": 1, "usb_port": [3],
        }

        with patch.object(pr, "UsbTransportWithPath") as mock_tp, patch.object(
            pr, "PaperangP2"
        ) as mock_p2:
            mock_transport = MagicMock()
            mock_tp.return_value = mock_transport
            mod._get_printer("test_eid")
            mock_tp.assert_called_once_with(bus=1, port=[3])
            mock_p2.assert_called_once_with(transport=mock_transport)

    async def test_get_printer_ble(self) -> None:
        """_get_printer with BLE transport uses BleTransport."""
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as pr

        mod._transport_configs.clear()
        mod._transport_configs["test_eid"] = {
            "transport": "ble", "ble_address": "AA:BB:CC:DD:EE:FF",
        }

        with patch.object(pr, "BleTransport", create=True) as mock_ble_cls, patch.object(
            pr, "PaperangP2"
        ) as mock_p2:
            mock_ble = MagicMock()
            mock_ble_cls.return_value = mock_ble
            mod._get_printer("test_eid")
            mock_ble_cls.assert_called_once_with(address="AA:BB:CC:DD:EE:FF")
            mock_p2.assert_called_once_with(transport=mock_ble)

    async def test_get_printer_ble_skipped_polling(self, hass: HomeAssistant) -> None:
        """BLE transport returns available=True without reading."""
        import custom_components.paperang as mod
        mod._transport_configs["test_eid"] = {
            "transport": "ble", "ble_address": "AA:BB:CC:DD:EE:FF",
        }

        result = await mod._read_printer_state(hass, "test_eid")
        assert result == {"available": True, "connected": "connected"}

    async def test_read_printer_state_firmware_decode(self, hass: HomeAssistant, mock_printer) -> None:
        """Firmware version 720897 is decoded to V1.0.11."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod
        mod._transport_configs[entry.entry_id] = dict(entry.data)

        with patch(_PATCH_RUNTIME_GET, return_value=mock_printer):
            result = await mod._read_printer_state(hass, entry.entry_id)

        assert result["version"] == "V1.0.11"

    async def test_read_printer_state_retry_failure(self, hass: HomeAssistant) -> None:
        """After all retries fail, returns unavailable."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod
        mod._transport_configs[entry.entry_id] = dict(entry.data)

        bad = MagicMock()
        bad.connect.side_effect = RuntimeError("boom")

        with patch(_PATCH_RUNTIME_GET, return_value=bad):
            result = await mod._read_printer_state(hass, entry.entry_id)

        assert result == {"available": False, "connected": "disconnected"}

    async def test_do_print_qr(self, mock_printer) -> None:
        """_do_print_qr calls print_qr with correct args."""
        import custom_components.paperang as mod

        with patch(_PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_qr("test", "https://x.com", 400, 70)

        mock_printer.print_qr.assert_called_once_with("https://x.com", heat_density=70, max_width=400)

    async def test_do_print_pickup_code(self, mock_printer) -> None:
        """_do_print_pickup_code calls print_pickup_code."""
        import custom_components.paperang as mod

        with patch(_PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_pickup_code("test", "19-4308")

        mock_printer.print_pickup_code.assert_called_once_with("19-4308")

    async def test_do_get_status_failure(self, hass: HomeAssistant) -> None:
        """_do_get_status returns error dict on failure."""
        import custom_components.paperang as mod

        with patch(_PATCH_RUNTIME_GET, side_effect=RuntimeError("offline")):
            result = mod._do_get_status("test")

        assert result["available"] is False
        assert result["battery"] is None

    async def test_get_printer_fallback(self) -> None:
        """_get_printer without args returns default PaperangP2."""
        import custom_components.paperang as mod
        import custom_components.paperang.core.runtime as pr

        mod._transport_configs.clear()

        with patch.object(pr, "PaperangP2") as mock_p2:
            mod._get_printer()
            mock_p2.assert_called_once()

    async def test_update_if_not_none(self) -> None:
        """_update_if_not_none updates when value is not None."""
        import custom_components.paperang as mod
        cache = {}
        mod._update_if_not_none(cache, "key", "value")
        assert cache["key"] == "value"
        mod._update_if_not_none(cache, "key", None)
        assert cache["key"] == "value"

    async def test_get_or_fallback(self) -> None:
        """_get_or_fallback returns cached value or None."""
        import custom_components.paperang as mod
        cache = {"a": 1}
        assert mod._get_or_fallback(cache, "a") == 1
        assert mod._get_or_fallback(cache, "b") is None

    async def test_get_static_dynamic_cache(self) -> None:
        """_get_static_cache and _get_dynamic_cache create and return per-entry dicts."""
        import custom_components.paperang as mod
        mod._static_caches.clear()
        mod._dynamic_caches.clear()
        sc = mod._get_static_cache("eid1")
        dc = mod._get_dynamic_cache("eid1")
        assert isinstance(sc, dict)
        assert isinstance(dc, dict)
        assert "eid1" in mod._static_caches
        assert mod._get_static_cache("eid1") is sc  # same object

    async def test_do_print_text(self, mock_printer) -> None:
        """_do_print_text calls print_text with correct args."""
        import custom_components.paperang as mod
        with patch(_PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_text("test", "Hello", 24, 75)
        mock_printer.print_text.assert_called_once_with("Hello", font_size=24, heat_density=75)

    async def test_do_print_image(self, mock_printer) -> None:
        """_do_print_image calls print_image with correct args."""
        import custom_components.paperang as mod
        with patch(_PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_image("test", image_url="http://img", heat_density=70, threshold=128, brightness=1.0, contrast=1.0)
        mock_printer.print_image.assert_called_once_with(
            "http://img", heat_density=70, threshold=128, brightness=1.0, contrast=1.0
        )
