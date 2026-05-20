"""Paperang P2 Printer - Button platform.

Provides pressable buttons on the device page for printer actions.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .entity import PaperangEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = f"paperang_{entry.entry_id}"
    device_info = DeviceInfo(
        identifiers={("paperang", device_id)},
    )

    async_add_entities(
        [
            PaperangPrintButton(coordinator, device_id, device_info, entry.entry_id),
            PaperangFeedButton(coordinator, device_id, device_info, entry.entry_id),
            PaperangTestPrintButton(coordinator, device_id, device_info, entry.entry_id),
        ]
    )


class PaperangPrintButton(PaperangEntity, ButtonEntity):
    """Print button — reads mode/content/params and fires the correct service."""

    def __init__(self, coordinator, device_id, device_info, entry_id) -> None:
        """Initialize."""
        super().__init__(
            coordinator, "Print", f"{device_id}_btn_print", "mdi:printer",
            device_info=device_info, entry_id=entry_id,
        )

    async def async_press(self) -> None:
        """Read entity states and dispatch the appropriate print service."""
        hass = self.hass
        prefix = f"select.paperang_{self._entry_id}_print_mode"

        mode = "text"
        content = ""
        font_size = 24
        heat_density = 75
        qr_size = 500
        profile = "document"

        if (state := hass.states.get(prefix)) is not None:
            mode = state.state
        if (state := hass.states.get(
            f"text.paperang_{self._entry_id}_print_content"
        )) is not None:
            content = state.state or ""
        if (state := hass.states.get(
            f"number.paperang_{self._entry_id}_font_size"
        )) is not None:
            font_size = int(float(state.state))
        if (state := hass.states.get(
            f"number.paperang_{self._entry_id}_heat_density"
        )) is not None:
            heat_density = int(float(state.state))
        if (state := hass.states.get(
            f"number.paperang_{self._entry_id}_qr_size"
        )) is not None:
            qr_size = int(float(state.state))
        if (state := hass.states.get(
            f"select.paperang_{self._entry_id}_image_profile"
        )) is not None:
            profile = state.state

        if not content.strip():
            _LOGGER.warning("Print content is empty")
            return

        svc_data = {"entry_id": self._entry_id}

        if mode == "text":
            svc_data.update({
                "text": content, "font_size": font_size, "heat_density": heat_density,
            })
            await hass.services.async_call(
                DOMAIN, "print_text", svc_data, blocking=False,
            )
        elif mode == "image":
            svc_data.update({
                "image_url": content, "heat_density": heat_density, "profile": profile,
            })
            await hass.services.async_call(
                DOMAIN, "print_image", svc_data, blocking=False,
            )
        elif mode == "qr":
            svc_data.update({
                "qr_content": content, "qr_size": qr_size, "heat_density": heat_density,
            })
            await hass.services.async_call(
                DOMAIN, "print_qr", svc_data, blocking=False,
            )
        elif mode == "pickup_code":
            svc_data.update({"pickup_code": content})
            await hass.services.async_call(
                DOMAIN, "print_pickup_code", svc_data, blocking=False,
            )


class PaperangFeedButton(PaperangEntity, ButtonEntity):
    """Feed paper button."""

    def __init__(self, coordinator, device_id, device_info, entry_id) -> None:
        """Initialize."""
        super().__init__(
            coordinator, "Feed Paper", f"{device_id}_btn_feed_paper",
            "mdi:arrow-down-bold", device_info=device_info, entry_id=entry_id,
        )

    async def async_press(self) -> None:
        """Feed paper."""
        lines = 50
        if (state := self.hass.states.get(
            f"number.paperang_{self._entry_id}_feed_lines"
        )) is not None:
            lines = int(float(state.state))
        await self.hass.services.async_call(
            DOMAIN, "feed_paper",
            {"lines": lines, "entry_id": self._entry_id},
            blocking=False,
        )


class PaperangTestPrintButton(PaperangEntity, ButtonEntity):
    """Test print button."""

    def __init__(self, coordinator, device_id, device_info, entry_id) -> None:
        """Initialize."""
        super().__init__(
            coordinator, "Test Print", f"{device_id}_btn_test_print",
            "mdi:printer-check", device_info=device_info, entry_id=entry_id,
        )

    async def async_press(self) -> None:
        """Print test page."""
        await self.hass.services.async_call(
            DOMAIN, "print_test_page",
            {"entry_id": self._entry_id},
            blocking=False,
        )
