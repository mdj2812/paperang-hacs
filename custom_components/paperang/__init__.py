"""Paperang P2 Printer integration for Home Assistant.

Powered by paperang-p2-lib for core printer logic.
"""

from __future__ import annotations

from datetime import timedelta
from functools import partial

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_TRANSPORT, DOMAIN, TRANSPORT_USB
from .core.paperang_lib import BleTransport, PaperangP2
from .core.blocking import (
    _do_feed_paper,
    _do_get_status,
    _do_print_image,
    _do_print_pickup_code,
    _do_print_qr,
    _do_print_test_page,
    _do_print_text,
    _with_printer,
)
from .core.runtime import _get_printer, transport_configs
from .core.state import (
    _dynamic_caches,
    _get_dynamic_cache,
    _get_or_fallback,
    _get_static_cache,
    _read_printer_state,
    _static_caches,
    _update_if_not_none,
    clear_caches_for_entry,
)
from .transport.usb import UsbTransportWithPath
from .services import async_setup_services

PLATFORMS = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TEXT,
]

UPDATE_INTERVAL = timedelta(seconds=5)

_LOGGER = logging.getLogger(__name__)

# Back-compat: tests and older code used ``_transport_configs``.
_transport_configs = transport_configs


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Paperang P2 Printer component."""
    async_setup_services(hass, config)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry):
    """Migrate config entry v1 → v2: add transport key."""
    if entry.version == 1:
        data = dict(entry.data)
        data.setdefault(CONF_TRANSPORT, TRANSPORT_USB)
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            version=2,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up from config entry (also called after YAML import)."""
    transport_configs[entry.entry_id] = dict(entry.data)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="paperang",
        update_method=partial(_read_printer_state, hass, entry.entry_id),
        update_interval=UPDATE_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Paperang coordinator data: %s", coordinator.data)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry."""
    transport_configs.pop(entry.entry_id, None)
    clear_caches_for_entry(entry.entry_id)
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry
) -> dict[str, object]:
    """Return static printer info for diagnostics.

    Static values (board version, firmware, hardware info, model,
    serial, paper type) are read once and cached; they belong in
    diagnostics rather than as live sensors.
    """
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not coordinator or not coordinator.data:
        return {}
    data = coordinator.data
    return {
        "board_version": data.get("board"),
        "firmware_version": data.get("version"),
        "hardware_info": data.get("hw_info"),
        "model": data.get("model"),
        "serial_number": data.get("serial"),
        "paper_type": data.get("paper_type"),
    }
