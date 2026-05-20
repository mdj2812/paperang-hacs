# pylint: disable=import-error,duplicate-code
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


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button platform from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = f"paperang_{entry.entry_id}"
    device_info = DeviceInfo(
        identifiers={("paperang", device_id)},
    )

    async_add_entities([
        PaperangPrintButton(coordinator, device_info, device_id, entry.entry_id),
        PaperangFeedButton(coordinator, device_info, device_id, entry.entry_id),
        PaperangTestPrintButton(coordinator, device_info, device_id, entry.entry_id),
    ])


class PaperangPrintButton(CoordinatorEntity, ButtonEntity):
    """Print button — reads mode/content/params and fires the correct service."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, device_info, device_id, entry_id) -> None:
        """Initialize."""
        self._attr_name = "Print"
        self._attr_unique_id = f"{device_id}_btn_print"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:printer"
        self._entry_id = entry_id
        super().__init__(coordinator)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

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

        service_data = {"entry_id": self._entry_id}

        if mode == "text":
            service_data.update({
                "text": content,
                "font_size": font_size,
                "heat_density": heat_density,
            })
            await hass.services.async_call(
                DOMAIN, "print_text", service_data, blocking=False,
            )
        elif mode == "image":
            service_data.update({
                "image_url": content,
                "heat_density": heat_density,
                "profile": profile,
            })
            await hass.services.async_call(
                DOMAIN, "print_image", service_data, blocking=False,
            )
        elif mode == "qr":
            service_data.update({
                "qr_content": content,
                "qr_size": qr_size,
                "heat_density": heat_density,
            })
            await hass.services.async_call(
                DOMAIN, "print_qr", service_data, blocking=False,
            )
        elif mode == "pickup_code":
            service_data.update({"pickup_code": content})
            await hass.services.async_call(
                DOMAIN, "print_pickup_code", service_data, blocking=False,
            )


class PaperangFeedButton(CoordinatorEntity, ButtonEntity):
    """Feed paper button."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, device_info, device_id, entry_id) -> None:
        """Initialize."""
        self._attr_name = "Feed Paper"
        self._attr_unique_id = f"{device_id}_btn_feed_paper"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:arrow-down-bold"
        self._entry_id = entry_id
        super().__init__(coordinator)

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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class PaperangTestPrintButton(CoordinatorEntity, ButtonEntity):
    """Test print button."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, device_info, device_id, entry_id) -> None:
        """Initialize."""
        self._attr_name = "Test Print"
        self._attr_unique_id = f"{device_id}_btn_test_print"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:printer-check"
        self._entry_id = entry_id
        super().__init__(coordinator)

    async def async_press(self) -> None:
        """Print test page."""
        await self.hass.services.async_call(
            DOMAIN, "print_test_page",
            {"entry_id": self._entry_id},
            blocking=False,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
