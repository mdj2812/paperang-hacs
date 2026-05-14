# pylint: disable=import-error
"""Paperang P2 Printer integration for Home Assistant.

Powered by paperang-p2-lib for core printer logic.
"""

import logging
import sys
import time
from datetime import timedelta
from functools import partial


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
try:
    from paperang.transport import BleTransport  # pylint: disable=no-member
except ImportError:
    BleTransport = None

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
    CONF_TRANSPORT,
    CONF_BLE_ADDRESS,
    TRANSPORT_USB,
    TRANSPORT_BLE,
)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.SELECT, Platform.NUMBER, Platform.TEXT]

SCAN_INTERVAL = timedelta(seconds=60)

# ── Transport config (stored at module level for blocking functions) ─────

_transport_config: dict[str, object] = {}

def _get_printer():
    """Create a PaperangP2 with the configured transport."""
    transport_type = _transport_config.get(CONF_TRANSPORT, "")
    if transport_type == TRANSPORT_BLE and BleTransport is not None:
        ble_addr = _transport_config.get(CONF_BLE_ADDRESS, "")
        ble = BleTransport(address=ble_addr) if ble_addr else BleTransport()
        return PaperangP2(transport=ble)
    return PaperangP2()

# ── Coordinator update logic ───────────────────────────────────

_static_data: dict[str, object] = {}
_dynamic_data: dict[str, object] = {}

# pylint: disable=duplicate-code
_RETRIES = 3

_STATIC_KEYS = [
    "voltage", "temperature", "heat_density", "paper_type",
    "version", "model", "serial", "board", "hw_info",
]

_STATIC_READERS = [
    ("voltage", lambda p: p.get_voltage()),
    ("temperature", lambda p: p.get_temperature()),
    ("heat_density", lambda p: p.get_heat_density()),
    ("paper_type", lambda p: p.get_paper_type()),
    ("version", lambda p: p.get_version()),
    ("model", lambda p: p.get_model()),
    ("serial", lambda p: p.get_sn()),
    ("board", lambda p: p.get_board_version()),
    ("hw_info", lambda p: p.get_hw_info()),
]


def _update_if_not_none(cache: dict[str, object], key: str, val: object) -> None:
    """Update cache if value is not None, otherwise keep existing."""
    if val is not None:
        cache[key] = val


def _get_or_fallback(cache: dict[str, object], key: str) -> object:
    """Get value from cache, return None if never seen."""
    return cache.get(key)


async def _read_printer_state(hass: HomeAssistant):
    """Read all printer telemetry (runs blocking USB in executor)."""
    return await hass.async_add_executor_job(_do_read_printer_state)


def _do_read_printer_state():
    """Blocking: connect to printer and read telemetry.

    Dynamic values (battery, status): read every poll.  If None, keep
    the last known value so gaps don't show as unavailable.

    Static values (voltage, temperature, firmware, etc.): read every
    poll until a non-None value is obtained; thereafter reuse cache.

    Retries up to 3 times on failure; logs warning if all fail.
    """
    for attempt in range(1, _RETRIES + 1):
        data: dict[str, object] = {"available": False}
        printer = _get_printer()
        try:
            printer.connect()

            # ── Dynamic: always read, fall back to last known ──────
            battery = printer.get_battery()
            time.sleep(0.2)
            status = printer.get_status()
            data["battery"] = (
                battery if battery is not None
                else _get_or_fallback(_dynamic_data, "battery")
            )
            data["status"] = (
                status if status is not None
                else _get_or_fallback(_dynamic_data, "status")
            )
            _update_if_not_none(_dynamic_data, "battery", battery)
            _update_if_not_none(_dynamic_data, "status", status)

            # ── Static: always read, update cache if non-None ─────
            for key, reader in _STATIC_READERS:
                time.sleep(0.2)
                val = reader(printer)
                _update_if_not_none(_static_data, key, val)

            # Merge all cached values into data
            for key in _STATIC_KEYS:
                data[key] = _get_or_fallback(_static_data, key)

            data["available"] = True
            return data
        except Exception as err:  # pylint: disable=broad-exception-caught
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
                _dynamic_data.clear()
        finally:
            printer.disconnect()

    return {"available": False}
# pylint: enable=duplicate-code

_LOGGER = logging.getLogger(__name__)

def _with_printer(fn):
    """Create a printer, connect, run *fn(printer)*, disconnect.

    Returns whatever *fn* returns.  Exceptions propagate to caller.
    """
    printer = _get_printer()
    try:
        printer.connect()
        return fn(printer)
    finally:
        printer.disconnect()


def _do_print_text(text, font_size, heat_density):
    """Blocking: print text."""
    _with_printer(lambda p: p.print_text(text, font_size=font_size, heat_density=heat_density))


def _do_print_image(image_url, heat_density, threshold, brightness, contrast):
    """Blocking: print image."""
    _with_printer(
        lambda p: p.print_image(
            image_url,
            heat_density=heat_density,
            threshold=threshold,
            brightness=brightness,
            contrast=contrast,
        )
    )


def _do_print_qr(qr_content, qr_size, heat_density):
    """Blocking: print QR code."""
    _with_printer(lambda p: p.print_qr(qr_content, heat_density=heat_density, max_width=qr_size))


def _do_print_pickup_code(pickup_code):
    """Blocking: print pickup code."""
    _with_printer(lambda p: p.print_pickup_code(pickup_code))


def _do_print_test_page():
    """Blocking: print test page."""
    _with_printer(lambda p: p.print_test_page())


def _do_feed_paper(lines):
    """Blocking: feed paper."""
    _with_printer(lambda p: p.feed(lines))


def _do_get_status():
    """Blocking: get printer battery and status."""
    try:
        return _with_printer(
            lambda p: {
                "battery": p.get_battery(),
                "status": p.get_status(),
                "available": True,
            }
        )
    except Exception as err:  # pylint: disable=broad-exception-caught
        return {"battery": None, "status": None, "available": False, "error": str(err)}


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

        profiles = await hass.async_add_executor_job(load_profiles)
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

    async def handle_get_status(_call: ServiceCall) -> None:
        """Handle get status service call."""
        result = await hass.async_add_executor_job(_do_get_status)
        _LOGGER.info("Paperang P2 status: %s", result)

    async def handle_feed_paper(call: ServiceCall) -> None:
        """Handle feed paper service call."""
        lines = call.data.get(ATTR_LINES, 100)
        await hass.async_add_executor_job(_do_feed_paper, lines)

    async def handle_print_test_page(_call: ServiceCall) -> None:
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


async def async_migrate_entry(hass: HomeAssistant, entry):
    """Migrate config entry v1 → v2: add transport key."""
    if entry.version == 1:
        data = dict(entry.data)
        data.setdefault(CONF_TRANSPORT, TRANSPORT_USB)
        hass.config_entries.async_update_entry(
            entry, data=data, version=2,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up from config entry (also called after YAML import)."""
    # Populate transport config for blocking functions
    _transport_config.clear()
    _transport_config.update(entry.data)

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
