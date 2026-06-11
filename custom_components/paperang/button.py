"""Paperang P2 Printer - Button platform.

Provides pressable buttons on the device page for printer actions.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .entity import PaperangEntity, make_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_info = make_device_info(entry)

    async_add_entities(
        [
            PaperangPrintButton(coordinator, entry.entry_id, device_info),
            PaperangFeedButton(coordinator, entry.entry_id, device_info),
            PaperangTestPrintButton(coordinator, entry.entry_id, device_info),
        ]
    )


class PaperangPrintButton(PaperangEntity, ButtonEntity):
    """Print button — reads mode/content/params and fires the correct service."""

    def __init__(self, coordinator, entry_id, device_info) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            entry_id,
            "Print",
            "btn_print",
            "mdi:printer",
            device_info=device_info,
        )

    @staticmethod
    def _get_state_by_unique_id(hass, entity_unique_id: str, fallback_entity_id: str):
        """Get entity state by unique_id, with entity_id fallback.

        HA auto-generates entity_ids from the entity name, which changes
        with the UI language (e.g. "print_content" → "da_yin_nei_rong" in
        Chinese).  We first try the stable unique_id, then fall back to
        the hardcoded entity_id for testing and backwards compatibility.
        """
        registry = er.async_get(hass)
        for entry in registry.entities.values():
            if entry.unique_id == entity_unique_id:
                return hass.states.get(entry.entity_id)
        # Fallback: entity_id lookup (for tests and pre-registry setups)
        return hass.states.get(fallback_entity_id)

    async def async_press(self) -> None:
        """Read entity states and dispatch the appropriate print service."""
        hass = self.hass
        eid = self._entry_id

        mode = "text"
        content = ""
        font_size = 24
        heat_density = 75
        qr_size = 500
        profile = "document"
        vertical = False

        if (
            state := self._get_state_by_unique_id(
                hass, f"paperang_{eid}_print_mode", f"select.paperang_{eid}_print_mode"
            )
        ) is not None:
            mode = state.state
        if (
            state := self._get_state_by_unique_id(
                hass,
                f"paperang_{eid}_print_content",
                f"text.paperang_{eid}_print_content",
            )
        ) is not None:
            content = state.state or ""
        if (
            state := self._get_state_by_unique_id(
                hass, f"paperang_{eid}_font_size", f"number.paperang_{eid}_font_size"
            )
        ) is not None:
            font_size = int(float(state.state))
        if (
            state := self._get_state_by_unique_id(
                hass,
                f"paperang_{eid}_heat_density",
                f"number.paperang_{eid}_heat_density",
            )
        ) is not None:
            heat_density = int(float(state.state))
        if (
            state := self._get_state_by_unique_id(
                hass, f"paperang_{eid}_qr_size", f"number.paperang_{eid}_qr_size"
            )
        ) is not None:
            qr_size = int(float(state.state))
        if (
            state := self._get_state_by_unique_id(
                hass,
                f"paperang_{eid}_image_profile",
                f"select.paperang_{eid}_image_profile",
            )
        ) is not None:
            profile = state.state

        if (
            state := self._get_state_by_unique_id(
                hass, f"paperang_{eid}_vertical", f"switch.paperang_{eid}_vertical"
            )
        ) is not None:
            vertical = state.state == "on"

        if not content.strip():
            _LOGGER.warning("Print content is empty")
            return

        svc_data = {"entry_id": eid}

        if mode == "text":
            svc_data.update(
                {
                    "text": content,
                    "font_size": font_size,
                    "heat_density": heat_density,
                    "vertical": vertical,
                }
            )
            await hass.services.async_call(
                DOMAIN,
                "print_text",
                svc_data,
                blocking=False,
            )
        elif mode == "image":
            svc_data.update(
                {
                    "image_url": content,
                    "heat_density": heat_density,
                    "profile": profile,
                    "vertical": vertical,
                }
            )
            await hass.services.async_call(
                DOMAIN,
                "print_image",
                svc_data,
                blocking=False,
            )
        elif mode == "qr":
            svc_data.update(
                {
                    "qr_content": content,
                    "qr_size": qr_size,
                    "heat_density": heat_density,
                    "vertical": vertical,
                }
            )
            await hass.services.async_call(
                DOMAIN,
                "print_qr",
                svc_data,
                blocking=False,
            )
        elif mode == "pickup_code":
            svc_data.update({"pickup_code": content, "vertical": vertical})
            await hass.services.async_call(
                DOMAIN,
                "print_pickup_code",
                svc_data,
                blocking=False,
            )


class PaperangFeedButton(PaperangEntity, ButtonEntity):
    """Feed paper button."""

    def __init__(self, coordinator, entry_id, device_info) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            entry_id,
            "Feed Paper",
            "btn_feed_paper",
            "mdi:arrow-down-bold",
            device_info=device_info,
        )

    async def async_press(self) -> None:
        """Feed paper."""
        eid = self._entry_id
        lines = 50
        if (
            state := self.hass.states.get(f"number.paperang_{eid}_feed_lines")
        ) is not None:
            lines = int(float(state.state))
        await self.hass.services.async_call(
            DOMAIN,
            "feed_paper",
            {"lines": lines, "entry_id": eid},
            blocking=False,
        )


class PaperangTestPrintButton(PaperangEntity, ButtonEntity):
    """Test print button."""

    def __init__(self, coordinator, entry_id, device_info) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            entry_id,
            "Test Print",
            "btn_test_print",
            "mdi:printer-check",
            device_info=device_info,
        )

    async def async_press(self) -> None:
        """Print test page."""
        await self.hass.services.async_call(
            DOMAIN,
            "print_test_page",
            {"entry_id": self._entry_id},
            blocking=False,
        )
