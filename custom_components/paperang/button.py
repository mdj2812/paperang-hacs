# pylint: disable=import-error
"""Paperang P2 Printer - Button platform.

Provides pressable buttons on the device page for printer actions.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEVICE_ID = "paperang_p2_printer"
DEVICE_INFO = DeviceInfo(
    identifiers={("paperang", DEVICE_ID)},
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        PaperangPrintButton(coordinator),
        PaperangFeedButton(coordinator),
        PaperangTestPrintButton(coordinator),
    ])


class PaperangPrintButton(CoordinatorEntity, ButtonEntity):
    """Print button — reads mode/content/params and fires the correct service."""

    _attr_has_entity_name = True

    def __init__(self, coordinator) -> None:
        """Initialize."""
        self._attr_name = "Print"
        self._attr_unique_id = "paperang_p2_btn_print"
        self._attr_device_info = DEVICE_INFO
        self._attr_icon = "mdi:printer"
        super().__init__(coordinator)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

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


class PaperangFeedButton(CoordinatorEntity, ButtonEntity):
    """Feed paper button."""

    _attr_has_entity_name = True

    def __init__(self, coordinator) -> None:
        """Initialize."""
        self._attr_name = "Feed Paper"
        self._attr_unique_id = "paperang_p2_btn_feed_paper"
        self._attr_device_info = DEVICE_INFO
        self._attr_icon = "mdi:arrow-down-bold"
        super().__init__(coordinator)

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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class PaperangTestPrintButton(CoordinatorEntity, ButtonEntity):
    """Test print button."""

    _attr_has_entity_name = True

    def __init__(self, coordinator) -> None:
        """Initialize."""
        self._attr_name = "Test Print"
        self._attr_unique_id = "paperang_p2_btn_test_print"
        self._attr_device_info = DEVICE_INFO
        self._attr_icon = "mdi:printer-check"
        super().__init__(coordinator)

    async def async_press(self) -> None:
        """Print test page."""
        await self.hass.services.async_call(
            DOMAIN, "print_test_page", {}, blocking=False,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
