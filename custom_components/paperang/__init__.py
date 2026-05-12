# pylint: disable=import-error
"""Paperang P2 Printer integration for Home Assistant.

Powered by paperang-p2-lib for core printer logic.
"""

import logging
import sys
import time
from datetime import timedelta
from functools import partial

import usb.util

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

# The pip-installed paperang-p2-lib shares the module name 'paperang'
# with this HA component. HA puts custom_components/ first in sys.path,
# so temporarily remove it to import the library correctly.
_custom_paths = [p for p in sys.path if 'custom_components' in p]
for _p in _custom_paths:
    sys.path.remove(_p)

import paperang as _lib  # pylint: disable=wrong-import-position,import-self

for _p in _custom_paths:
    sys.path.insert(0, _p)

PaperangP2 = _lib.PaperangP2  # pylint: disable=no-member
load_profiles = _lib.load_profiles  # pylint: disable=no-member
crc32_paperang = _lib.crc32_paperang  # pylint: disable=no-member
pack_packet = _lib.pack_packet  # pylint: disable=no-member

from .const import (  # pylint: disable=wrong-import-position
    DOMAIN,
    SERVICE_PRINT_TEXT,
    SERVICE_PRINT_IMAGE,
    SERVICE_PRINT_QR,
    SERVICE_PRINT_PICKUP_CODE,
    SERVICE_GET_STATUS,
    SERVICE_FEED_PAPER,
    SERVICE_PRINT_TEST_PAGE,
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

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

SCAN_INTERVAL = timedelta(seconds=60)

# ── Coordinator update logic ───────────────────────────────────

_static_data: dict[str, object] = {}

# pylint: disable=duplicate-code
_RETRIES = 3

async def _read_printer_state(hass: HomeAssistant):
    """Read all printer telemetry (runs blocking USB in executor)."""
    return await hass.async_add_executor_job(_do_read_printer_state)


def _do_read_printer_state():
    """Blocking: connect to printer and read telemetry.

    Always reads battery + status (dynamic).
    Static fields (voltage, temperature, firmware, etc.) are read once
    on first connect or reconnect, then cached until disconnection.
    Retries up to 3 times on failure; logs warning if all fail.
    """
    for attempt in range(1, _RETRIES + 1):
        data = {"available": False}
        printer = PaperangP2()
        try:
            printer.connect()

            data["battery"] = printer.get_battery()
            time.sleep(0.2)
            data["status"] = printer.get_status()

            if _static_data:
                data.update(_static_data)
            else:
                time.sleep(0.2)
                data["voltage"] = printer.get_voltage()
                time.sleep(0.2)
                data["temperature"] = printer.get_temperature()
                time.sleep(0.2)
                data["heat_density"] = printer.get_heat_density()
                time.sleep(0.2)
                data["paper_type"] = printer.get_paper_type()
                time.sleep(0.2)
                data["version"] = printer.get_version()
                time.sleep(0.2)
                data["model"] = printer.get_model()
                time.sleep(0.2)
                data["serial"] = printer.get_sn()
                time.sleep(0.2)
                data["board"] = printer.get_board_version()
                time.sleep(0.2)
                data["hw_info"] = printer.get_hw_info()

                _static_data.clear()
                _static_data.update({
                    k: v for k, v in data.items()
                    if k not in ("battery", "status", "available")
                })

            data["available"] = True
            return data
        except Exception as err:
            if attempt < _RETRIES:
                _LOGGER.debug(
                    "Printer read attempt %d/%d failed: %s",
                    attempt, _RETRIES, err,
                )
            else:
                _LOGGER.warning(
                    "Printer not available after %d attempts: %s",
                    _RETRIES, err,
                )
                _static_data.clear()
        finally:
            if printer.dev:
                try:
                    usb.util.dispose_resources(printer.dev)
                except Exception:
                    pass

    return {"available": False}
# pylint: enable=duplicate-code

_LOGGER = logging.getLogger(__name__)


def _safe_cleanup(printer):
    """Safely release USB resources."""
    if hasattr(printer, "dev") and printer.dev:
        try:
            usb.util.dispose_resources(printer.dev)
        except Exception:
            pass


def _do_print_text(text, font_size, heat_density):
    """Blocking: print text."""
    printer = PaperangP2()
    try:
        printer.connect()
        printer.print_text(text, font_size=font_size, heat_density=heat_density)
    finally:
        _safe_cleanup(printer)


def _do_print_image(image_url, heat_density, threshold, brightness, contrast):
    """Blocking: print image."""
    printer = PaperangP2()
    try:
        printer.connect()
        printer.print_image(
            image_url,
            heat_density=heat_density,
            threshold=threshold,
            brightness=brightness,
            contrast=contrast,
        )
    finally:
        _safe_cleanup(printer)


def _do_print_qr(qr_content, qr_size, heat_density):
    """Blocking: print QR code."""
    printer = PaperangP2()
    try:
        printer.connect()
        printer.print_qr(qr_content, heat_density=heat_density, max_width=qr_size)
    finally:
        _safe_cleanup(printer)


def _do_print_pickup_code(pickup_code):
    """Blocking: print pickup code."""
    printer = PaperangP2()
    try:
        printer.connect()
        printer.print_pickup_code(pickup_code)
    finally:
        _safe_cleanup(printer)


def _do_print_test_page():
    """Blocking: print test page."""
    printer = PaperangP2()
    try:
        printer.connect()
        printer.print_test_page()
    finally:
        _safe_cleanup(printer)


def _do_get_status():
    """Blocking: get printer battery and status."""
    printer = PaperangP2()
    try:
        printer.connect()
        battery = printer.get_battery()
        status = printer.get_status()
        return {"battery": battery, "status": status, "available": True}
    except Exception as err:
        return {"battery": None, "status": None, "available": False, "error": str(err)}
    finally:
        _safe_cleanup(printer)


def _do_feed_paper(lines):
    """Blocking: feed paper."""
    printer = PaperangP2()
    try:
        printer.connect()
        printer.feed(lines)
    finally:
        _safe_cleanup(printer)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Paperang P2 Printer component."""
    # Register services


    async def handle_print_text(call: ServiceCall) -> None:
        """Handle print text service call."""
        text = call.data.get(ATTR_TEXT, "")
        font_size = call.data.get(ATTR_FONT_SIZE, 24)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)
        await hass.async_add_executor_job(_do_print_text, text, font_size, heat_density)

    async def handle_print_image(call: ServiceCall) -> None:
        """Handle print image service call."""
        image_url = call.data.get(ATTR_IMAGE_URL, "")
        profile = call.data.get(ATTR_PROFILE)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)

        profiles = load_profiles()
        profile_settings = profiles.get(profile, {}) if profile else {}

        threshold = profile_settings.get("threshold", 128)
        brightness = profile_settings.get("brightness", 1.0)
        contrast = profile_settings.get("contrast", 1.0)
        if "heat_density" in profile_settings:
            heat_density = profile_settings["heat_density"]

        await hass.async_add_executor_job(
            _do_print_image, image_url, heat_density, threshold, brightness, contrast
        )

    async def handle_print_qr(call: ServiceCall) -> None:
        """Handle print QR code service call."""
        qr_content = call.data.get(ATTR_QR_CONTENT, "")
        qr_size = call.data.get(ATTR_QR_SIZE, 500)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)
        await hass.async_add_executor_job(_do_print_qr, qr_content, qr_size, heat_density)

    async def handle_print_pickup_code(call: ServiceCall) -> None:
        """Handle print pickup code service call."""
        pickup_code = call.data.get(ATTR_PICKUP_CODE, "")
        await hass.async_add_executor_job(_do_print_pickup_code, pickup_code)

    async def handle_get_status(call: ServiceCall) -> None:  # pylint: disable=unused-argument
        """Handle get status service call."""
        result = await hass.async_add_executor_job(_do_get_status)
        _LOGGER.info("Paperang P2 status: %s", result)

    async def handle_feed_paper(call: ServiceCall) -> None:
        """Handle feed paper service call."""
        lines = call.data.get(ATTR_LINES, 100)
        await hass.async_add_executor_job(_do_feed_paper, lines)

    async def handle_print_test_page(call: ServiceCall) -> None:  # pylint: disable=unused-argument
        """Handle print test page service call."""
        await hass.async_add_executor_job(_do_print_test_page)

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_PRINT_TEXT, handle_print_text)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_IMAGE, handle_print_image)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_QR, handle_print_qr)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_PICKUP_CODE, handle_print_pickup_code)
    hass.services.async_register(DOMAIN, SERVICE_GET_STATUS, handle_get_status)
    hass.services.async_register(DOMAIN, SERVICE_FEED_PAPER, handle_feed_paper)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_TEST_PAGE, handle_print_test_page)

    _LOGGER.info("Paperang P2 Printer integration loaded")

    if DOMAIN in config and not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=config[DOMAIN],
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up from config entry (also called after YAML import)."""
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="paperang",
        update_method=partial(_read_printer_state, hass),
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Paperang coordinator data: %s", coordinator.data)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
