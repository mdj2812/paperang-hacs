"""Tests for paperang button platform — HA core style."""
import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import (
    DOMAIN,
    ATTR_TEXT,
    ATTR_FONT_SIZE,
    ATTR_HEAT_DENSITY,
    ATTR_IMAGE_URL,
    ATTR_PROFILE,
    ATTR_QR_CONTENT,
    ATTR_QR_SIZE,
    ATTR_PICKUP_CODE,
    ATTR_LINES,
)


pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def _setup_coordinator(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up a config entry with a mock coordinator."""
    from unittest.mock import MagicMock

    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"battery": 80, "status": "online"}
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator


class TestPrintButton:
    async def test_empty_content_warns(self, hass: HomeAssistant) -> None:
        """Empty content → warning, no service call."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.button import PaperangPrintButton
        btn = PaperangPrintButton(hass.data[DOMAIN][entry.entry_id])
        btn.hass = hass

        calls = []
        async def _spy(call):
            calls.append(call.data)
        for svc in ("print_text", "print_image", "print_qr", "print_pickup_code"):
            hass.services.async_register(DOMAIN, svc, _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 0

    async def test_text_mode(self, hass: HomeAssistant) -> None:
        """Text mode calls print_text service."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        hass.states.async_set("select.paperang_p2_printer_print_mode", "text")
        hass.states.async_set("text.paperang_p2_printer_print_content", "Hello")
        hass.states.async_set("number.paperang_p2_printer_font_size", "24")
        hass.states.async_set("number.paperang_p2_printer_heat_density", "75")

        from custom_components.paperang.button import PaperangPrintButton
        btn = PaperangPrintButton(hass.data[DOMAIN][entry.entry_id])
        btn.hass = hass

        calls = []
        async def _spy(call):
            calls.append(call.data)
        hass.services.async_register(DOMAIN, "print_text", _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0][ATTR_TEXT] == "Hello"
        assert calls[0][ATTR_FONT_SIZE] == 24
        assert calls[0][ATTR_HEAT_DENSITY] == 75

    async def test_image_mode(self, hass: HomeAssistant) -> None:
        """Image mode calls print_image service."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        hass.states.async_set("select.paperang_p2_printer_print_mode", "image")
        hass.states.async_set("text.paperang_p2_printer_print_content", "http://img")
        hass.states.async_set("number.paperang_p2_printer_heat_density", "80")
        hass.states.async_set("select.paperang_p2_printer_image_profile", "photo")

        from custom_components.paperang.button import PaperangPrintButton
        btn = PaperangPrintButton(hass.data[DOMAIN][entry.entry_id])
        btn.hass = hass

        calls = []
        async def _spy(call):
            calls.append(call.data)
        hass.services.async_register(DOMAIN, "print_image", _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0][ATTR_IMAGE_URL] == "http://img"
        assert calls[0][ATTR_HEAT_DENSITY] == 80
        assert calls[0][ATTR_PROFILE] == "photo"

    async def test_qr_mode(self, hass: HomeAssistant) -> None:
        """QR mode calls print_qr service."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        hass.states.async_set("select.paperang_p2_printer_print_mode", "qr")
        hass.states.async_set("text.paperang_p2_printer_print_content", "https://x.com")
        hass.states.async_set("number.paperang_p2_printer_qr_size", "400")
        hass.states.async_set("number.paperang_p2_printer_heat_density", "60")

        from custom_components.paperang.button import PaperangPrintButton
        btn = PaperangPrintButton(hass.data[DOMAIN][entry.entry_id])
        btn.hass = hass

        calls = []
        async def _spy(call):
            calls.append(call.data)
        hass.services.async_register(DOMAIN, "print_qr", _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0][ATTR_QR_CONTENT] == "https://x.com"
        assert calls[0][ATTR_QR_SIZE] == 400
        assert calls[0][ATTR_HEAT_DENSITY] == 60

    async def test_pickup_code_mode(self, hass: HomeAssistant) -> None:
        """Pickup code mode calls print_pickup_code service."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        hass.states.async_set("select.paperang_p2_printer_print_mode", "pickup_code")
        hass.states.async_set("text.paperang_p2_printer_print_content", "19-4308")

        from custom_components.paperang.button import PaperangPrintButton
        btn = PaperangPrintButton(hass.data[DOMAIN][entry.entry_id])
        btn.hass = hass

        calls = []
        async def _spy(call):
            calls.append(call.data)
        hass.services.async_register(DOMAIN, "print_pickup_code", _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0][ATTR_PICKUP_CODE] == "19-4308"


class TestFeedButton:
    async def test_feed_paper(self, hass: HomeAssistant) -> None:
        """Feed button calls feed_paper service."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        hass.states.async_set("number.paperang_p2_printer_feed_lines", "10")

        from custom_components.paperang.button import PaperangFeedButton
        btn = PaperangFeedButton(hass.data[DOMAIN][entry.entry_id])
        btn.hass = hass

        calls = []
        async def _spy(call):
            calls.append(call.data)
        hass.services.async_register(DOMAIN, "feed_paper", _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0][ATTR_LINES] == 10

    async def test_feed_paper_default_lines(self, hass: HomeAssistant) -> None:
        """Feed button defaults to 50 lines when entity not found."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.button import PaperangFeedButton
        btn = PaperangFeedButton(hass.data[DOMAIN][entry.entry_id])
        btn.hass = hass

        calls = []
        async def _spy(call):
            calls.append(call.data)
        hass.services.async_register(DOMAIN, "feed_paper", _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 1
        assert calls[0][ATTR_LINES] == 50


class TestTestPrintButton:
    async def test_test_print(self, hass: HomeAssistant) -> None:
        """Test print button calls print_test_page service."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.button import PaperangTestPrintButton
        btn = PaperangTestPrintButton(hass.data[DOMAIN][entry.entry_id])
        btn.hass = hass

        calls = []
        async def _spy(call):
            calls.append(call.data)
        hass.services.async_register(DOMAIN, "print_test_page", _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 1
