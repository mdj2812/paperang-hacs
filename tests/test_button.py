"""Tests for paperang button platform — HA core style."""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
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


def _make_btn(cls, hass, entry):
    """Create a button entity with per-entry args."""
    eid = entry.entry_id
    device_id = f"paperang_{eid}"
    device_info = DeviceInfo(identifiers={("paperang", device_id)})
    btn = cls(hass.data[DOMAIN][eid], device_id, device_info, eid)
    btn.hass = hass
    return btn


class TestPrintButton:
    async def test_empty_content_warns(self, hass: HomeAssistant) -> None:
        """Empty content → warning, no service call."""
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_hass(hass)
        await _setup_coordinator(hass, entry)

        from custom_components.paperang.button import PaperangPrintButton

        eid = entry.entry_id
        btn = _make_btn(PaperangPrintButton, hass, entry)

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

        eid = entry.entry_id
        hass.states.async_set(f"select.paperang_{eid}_print_mode", "text")
        hass.states.async_set(f"text.paperang_{eid}_print_content", "Hello")
        hass.states.async_set(f"number.paperang_{eid}_font_size", "24")
        hass.states.async_set(f"number.paperang_{eid}_heat_density", "75")

        from custom_components.paperang.button import PaperangPrintButton

        btn = _make_btn(PaperangPrintButton, hass, entry)

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

        eid = entry.entry_id
        hass.states.async_set(f"select.paperang_{eid}_print_mode", "image")
        hass.states.async_set(f"text.paperang_{eid}_print_content", "http://img")
        hass.states.async_set(f"number.paperang_{eid}_heat_density", "80")
        hass.states.async_set(f"select.paperang_{eid}_image_profile", "photo")

        from custom_components.paperang.button import PaperangPrintButton

        btn = _make_btn(PaperangPrintButton, hass, entry)

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

        eid = entry.entry_id
        hass.states.async_set(f"select.paperang_{eid}_print_mode", "qr")
        hass.states.async_set(f"text.paperang_{eid}_print_content", "https://x.com")
        hass.states.async_set(f"number.paperang_{eid}_qr_size", "400")
        hass.states.async_set(f"number.paperang_{eid}_heat_density", "60")

        from custom_components.paperang.button import PaperangPrintButton

        btn = _make_btn(PaperangPrintButton, hass, entry)

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

        eid = entry.entry_id
        hass.states.async_set(f"select.paperang_{eid}_print_mode", "pickup_code")
        hass.states.async_set(f"text.paperang_{eid}_print_content", "19-4308")

        from custom_components.paperang.button import PaperangPrintButton

        btn = _make_btn(PaperangPrintButton, hass, entry)

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

        eid = entry.entry_id
        hass.states.async_set(f"number.paperang_{eid}_feed_lines", "10")

        from custom_components.paperang.button import PaperangFeedButton

        btn = _make_btn(PaperangFeedButton, hass, entry)

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

        btn = _make_btn(PaperangFeedButton, hass, entry)

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

        btn = _make_btn(PaperangTestPrintButton, hass, entry)

        calls = []

        async def _spy(call):
            calls.append(call.data)

        hass.services.async_register(DOMAIN, "print_test_page", _spy)

        await btn.async_press()
        await hass.async_block_till_done()

        assert len(calls) == 1
