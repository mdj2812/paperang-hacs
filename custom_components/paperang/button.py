"""Paperang P2 Printer - Button platform.

Provides pressable buttons on the device page for printer actions.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import PaperangEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        PaperangPrintButton(coordinator),
        PaperangFeedButton(coordinator),
        PaperangTestPrintButton(coordinator),
    ])


class PaperangPrintButton(PaperangEntity, ButtonEntity):
    """Print button — reads mode/content/params and fires the correct service."""

    def __init__(self, coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "Print", "paperang_p2_btn_print", "mdi:printer")

    async def async_press(self) -> None:
        """Read entity states and dispatch the appropriate print service."""
        hass = self.hass
        prefix = "select.paperang_p2_printer_print_mode"

        mode = "text"
        content = ""
        font_size = 24
        heat_density = 75
        qr_size = 500
        profile = "document"

        if (state := hass.states.get(prefix)) is not None:
            mode = state.state
        if (state := hass.states.get("text.paperang_p2_printer_print_content")) is not None:
            content = state.state or ""
        if (state := hass.states.get("number.paperang_p2_printer_font_size")) is not None:
            font_size = int(float(state.state))
        if (state := hass.states.get("number.paperang_p2_printer_heat_density")) is not None:
            heat_density = int(float(state.state))
        if (state := hass.states.get("number.paperang_p2_printer_qr_size")) is not None:
            qr_size = int(float(state.state))
        if (state := hass.states.get("select.paperang_p2_printer_image_profile")) is not None:
            profile = state.state

        if not content.strip():
            _LOGGER.warning("Print content is empty")
            return

        if mode == "text":
            await hass.services.async_call(
                DOMAIN, "print_text",
                {"text": content, "font_size": font_size, "heat_density": heat_density},
                blocking=False,
            )
        elif mode == "image":
            await hass.services.async_call(
                DOMAIN, "print_image",
                {"image_url": content, "heat_density": heat_density, "profile": profile},
                blocking=False,
            )
        elif mode == "qr":
            await hass.services.async_call(
                DOMAIN, "print_qr",
                {"qr_content": content, "qr_size": qr_size, "heat_density": heat_density},
                blocking=False,
            )
        elif mode == "pickup_code":
            await hass.services.async_call(
                DOMAIN, "print_pickup_code",
                {"pickup_code": content},
                blocking=False,
            )


class PaperangFeedButton(PaperangEntity, ButtonEntity):
    """Feed paper button."""

    def __init__(self, coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "Feed Paper", "paperang_p2_btn_feed_paper", "mdi:arrow-down-bold")

    async def async_press(self) -> None:
        """Feed paper."""
        lines = 50
        if (state := self.hass.states.get(
            "number.paperang_p2_printer_feed_lines"
        )) is not None:
            lines = int(float(state.state))
        await self.hass.services.async_call(
            DOMAIN, "feed_paper", {"lines": lines}, blocking=False,
        )


class PaperangTestPrintButton(PaperangEntity, ButtonEntity):
    """Test print button."""

    def __init__(self, coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "Test Print", "paperang_p2_btn_test_print", "mdi:printer-check")

    async def async_press(self) -> None:
        """Print test page."""
        await self.hass.services.async_call(
            DOMAIN, "print_test_page", {}, blocking=False,
        )
