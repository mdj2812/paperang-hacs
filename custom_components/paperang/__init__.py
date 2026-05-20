"""Paperang P2 Printer integration for Home Assistant.

Powered by paperang-p2-lib for core printer logic.
"""

import logging
import sys
import time
from datetime import timedelta
from functools import partial

import paperang as _lib  # pylint: disable=import-self
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_FONT_SIZE,
    ATTR_HEAT_DENSITY,
    ATTR_IMAGE_URL,
    ATTR_LINES,
    ATTR_PICKUP_CODE,
    ATTR_PROFILE,
    ATTR_QR_CONTENT,
    ATTR_QR_SIZE,
    ATTR_TEXT,
    CONF_BLE_ADDRESS,
    CONF_TRANSPORT,
    CONF_USB_BUS,
    CONF_USB_PORT,
    DOMAIN,
    SERVICE_FEED_PAPER,
    SERVICE_GET_STATUS,
    SERVICE_PRINT_IMAGE,
    SERVICE_PRINT_PICKUP_CODE,
    SERVICE_PRINT_QR,
    SERVICE_PRINT_TEST_PAGE,
    SERVICE_PRINT_TEXT,
    TRANSPORT_BLE,
    TRANSPORT_USB,
)

# The pip-installed paperang-p2-lib shares the module name 'paperang'
# with this HA component. HA puts custom_components/ first in sys.path,
# so temporarily remove it to import the library correctly.
_custom_paths = [p for p in sys.path if "custom_components" in p]
for _p in _custom_paths:
    sys.path.remove(_p)


for _p in _custom_paths:
    sys.path.insert(0, _p)

PaperangP2 = _lib.PaperangP2  # pylint: disable=no-member
load_profiles = _lib.load_profiles  # pylint: disable=no-member
crc32_paperang = _lib.crc32_paperang  # pylint: disable=no-member
pack_packet = _lib.pack_packet  # pylint: disable=no-member
try:
    from paperang.transport import BleTransport
except ImportError:
    BleTransport = None

PLATFORMS = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TEXT,
]

UPDATE_INTERVAL = timedelta(seconds=5)

# pylint: disable=too-many-instance-attributes,attribute-defined-outside-init
# pylint: disable=no-member,too-few-public-methods,import-outside-toplevel


class UsbTransportWithPath(_lib.transport.UsbTransport):
    """UsbTransport that connects to a specific device by bus/port.

    The default *UsbTransport* always picks the first matching VID/PID
    device.  This subclass lets us pin a specific physical printer when
    multiple are attached.
    """

    def __init__(self, bus, port, vid=0x4348, pid=0x5584):
        super().__init__(vid, pid)
        self._target_bus = bus
        self._target_port = tuple(port) if port else ()

    def connect(self):
        """Find the targeted USB device, claim and configure it."""
        import usb.core
        import usb.util

        # Find all matching devices, pick the one at the right bus/port
        devices = usb.core.find(find_all=True, idVendor=self.vid, idProduct=self.pid)
        self._dev = None
        for d in devices:
            if d.bus == self._target_bus and tuple(d.port_numbers) == self._target_port:
                self._dev = d
                break

        if self._dev is None:
            raise RuntimeError(
                f"Paperang P2 not found at bus={self._target_bus} "
                f"port={list(self._target_port)}"
            )

        if self._dev.is_kernel_driver_active(0):
            self._dev.detach_kernel_driver(0)
        self._dev.set_configuration()
        cfg = self._dev.get_active_configuration()
        intf = cfg[(0, 0)]
        self._ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            ),
        )
        self._ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            ),
        )
        return True


# pylint: enable=too-many-instance-attributes,no-member,too-few-public-methods
# pylint: enable=import-outside-toplevel

# ── Per-entry transport config ───────────────────────────────────

_transport_configs: dict[str, dict[str, object]] = {}


def _get_printer(entry_id: str | None = None):
    """Create a PaperangP2 with the configured transport.

    When *entry_id* is given the matching config entry is used;
    otherwise the first configured entry is returned.
    """
    if entry_id and entry_id in _transport_configs:
        cfg = _transport_configs[entry_id]
    elif _transport_configs:
        entry_id, cfg = next(iter(_transport_configs.items()))
    else:
        return PaperangP2()

    transport_type = cfg.get(CONF_TRANSPORT, "")
    if transport_type == TRANSPORT_BLE and BleTransport is not None:
        ble_addr = cfg.get(CONF_BLE_ADDRESS, "")
        ble = BleTransport(address=ble_addr) if ble_addr else BleTransport()
        return PaperangP2(transport=ble)

    # USB — use targeted transport when bus/port are configured
    bus = cfg.get(CONF_USB_BUS)
    port = cfg.get(CONF_USB_PORT)
    if bus is not None and port is not None:
        return PaperangP2(transport=UsbTransportWithPath(bus=bus, port=port))

    return PaperangP2()


# ── Per-entry coordinator caches  ────────────────────────────────

_static_caches: dict[str, dict[str, object]] = {}
_dynamic_caches: dict[str, dict[str, object]] = {}


def _get_static_cache(entry_id: str) -> dict[str, object]:
    """Get or create the static cache for an entry."""
    if entry_id not in _static_caches:
        _static_caches[entry_id] = {}
    return _static_caches[entry_id]


def _get_dynamic_cache(entry_id: str) -> dict[str, object]:
    """Get or create the dynamic cache for an entry."""
    if entry_id not in _dynamic_caches:
        _dynamic_caches[entry_id] = {}
    return _dynamic_caches[entry_id]


_RETRIES = 3

_STATIC_KEYS = [
    "voltage",
    "temperature",
    "heat_density",
    "paper_type",
    "version",
    "model",
    "serial",
    "board",
    "hw_info",
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


async def _read_printer_state(hass: HomeAssistant, entry_id: str):
    """Read all printer telemetry.

    USB: blocking I/O in executor thread.
    BLE: skip polling — BLE only connects during on-demand operations.
    """
    cfg = _transport_configs.get(entry_id, {})
    if cfg.get(CONF_TRANSPORT) == TRANSPORT_BLE:
        return {"available": True}
    return await hass.async_add_executor_job(_do_read_printer_state, entry_id)


def _do_read_printer_state(entry_id: str):
    """Blocking: connect to printer and read telemetry.

    Dynamic values (battery, status): read every poll.  If None, keep
    the last known value so gaps don't show as unavailable.

    Static values (voltage, temperature, firmware, etc.): read every
    poll until a non-None value is obtained; thereafter reuse cache.

    Retries up to 3 times on failure; logs warning if all fail.
    """
    for attempt in range(1, _RETRIES + 1):
        data: dict[str, object] = {"available": False}
        static_cache = _get_static_cache(entry_id)
        dynamic_cache = _get_dynamic_cache(entry_id)
        printer = _get_printer(entry_id)
        try:
            printer.connect()

            # ── Dynamic: always read, fall back to last known ──────
            battery = printer.get_battery()
            time.sleep(0.05)
            status = printer.get_status()
            data["battery"] = (
                battery
                if battery is not None
                else _get_or_fallback(dynamic_cache, "battery")
            )
            data["status"] = (
                status
                if status is not None
                else _get_or_fallback(dynamic_cache, "status")
            )
            _update_if_not_none(dynamic_cache, "battery", battery)
            _update_if_not_none(dynamic_cache, "status", status)

            # ── Static: always read, update cache if non-None ─────
            for key, reader in _STATIC_READERS:
                time.sleep(0.05)
                val = reader(printer)
                # Decode firmware version: raw str "720897" → "V1.0.11"
                # bits 0-7=major, 8-15=minor, 16-31=patch
                if key == "version" and val is not None:
                    try:
                        ver_int = int(val)
                        val = (
                            f"V{ver_int & 0xFF}."
                            f"{(ver_int >> 8) & 0xFF}."
                            f"{(ver_int >> 16) & 0xFFFF}"
                        )
                    except (ValueError, TypeError):
                        pass  # already readable
                _update_if_not_none(static_cache, key, val)

            # Merge all cached values into data
            for key in _STATIC_KEYS:
                data[key] = _get_or_fallback(static_cache, key)
            # Decode firmware version if still raw in cache
            ver = data.get("version")
            if ver is not None:
                try:
                    ver_int = int(ver)
                    data["version"] = (
                        f"V{ver_int & 0xFF}."
                        f"{(ver_int >> 8) & 0xFF}."
                        f"{(ver_int >> 16) & 0xFFFF}"
                    )
                except (ValueError, TypeError):
                    pass

            data["available"] = True
            return data
        except Exception as err:  # pylint: disable=broad-exception-caught
            if attempt < _RETRIES:
                _LOGGER.debug(
                    "Printer read attempt %d/%d failed: %s",
                    attempt,
                    _RETRIES,
                    err,
                )
            else:
                _LOGGER.warning(
                    "Printer not available after %d attempts: %s",
                    _RETRIES,
                    err,
                )
                _static_caches.pop(entry_id, None)
                _dynamic_caches.pop(entry_id, None)
        finally:
            printer.disconnect()

    return {"available": False}


# pylint: enable=duplicate-code

_LOGGER = logging.getLogger(__name__)


def _with_printer(entry_id: str, fn):
    """Create a printer, connect, run *fn(printer)*, disconnect."""
    printer = _get_printer(entry_id)
    try:
        printer.connect()
        return fn(printer)
    finally:
        printer.disconnect()


def _do_print_text(entry_id, text, font_size, heat_density):
    """Blocking: print text."""
    _with_printer(
        entry_id,
        lambda p: p.print_text(text, font_size=font_size, heat_density=heat_density),
    )


def _do_print_image(
    entry_id, *, image_url, heat_density, threshold, brightness, contrast
):  # pylint: disable=too-many-arguments
    """Blocking: print image."""
    _with_printer(
        entry_id,
        lambda p: p.print_image(
            image_url,
            heat_density=heat_density,
            threshold=threshold,
            brightness=brightness,
            contrast=contrast,
        ),
    )


def _do_print_qr(entry_id, qr_content, qr_size, heat_density):
    """Blocking: print QR code."""
    _with_printer(
        entry_id,
        lambda p: p.print_qr(qr_content, heat_density=heat_density, max_width=qr_size),
    )


def _do_print_pickup_code(entry_id, pickup_code):
    """Blocking: print pickup code."""
    _with_printer(entry_id, lambda p: p.print_pickup_code(pickup_code))


def _do_print_test_page(entry_id):
    """Blocking: print test page."""
    _with_printer(entry_id, lambda p: p.print_test_page())


def _do_feed_paper(entry_id, lines):
    """Blocking: feed paper."""
    _with_printer(entry_id, lambda p: p.feed(lines))


def _do_get_status(entry_id):
    """Blocking: get printer battery and status."""
    try:
        return _with_printer(
            entry_id,
            lambda p: {
                "battery": p.get_battery(),
                "status": p.get_status(),
                "available": True,
            },
        )
    except Exception as err:  # pylint: disable=broad-exception-caught
        return {"battery": None, "status": None, "available": False, "error": str(err)}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Paperang P2 Printer component."""
    # pylint: disable=too-many-statements

    def _get_entry_id(call: ServiceCall) -> str:
        """Resolve entry_id from a service call."""
        explicit = call.data.get("entry_id")
        if explicit and explicit in _transport_configs:
            return explicit
        if _transport_configs:
            return next(iter(_transport_configs))
        return ""

    async def handle_print_text(call: ServiceCall) -> None:
        """Handle print text service call."""
        entry_id = _get_entry_id(call)
        if not entry_id:
            return
        text = call.data.get(ATTR_TEXT, "")
        font_size = call.data.get(ATTR_FONT_SIZE, 24)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)
        await hass.async_add_executor_job(
            _do_print_text, entry_id, text, font_size, heat_density
        )

    async def handle_print_image(call: ServiceCall) -> None:
        """Handle print image service call."""
        entry_id = _get_entry_id(call)
        if not entry_id:
            return
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
            _do_print_image,
            entry_id,
            image_url=image_url,
            heat_density=heat_density,
            threshold=threshold,
            brightness=brightness,
            contrast=contrast,
        )

    async def handle_print_qr(call: ServiceCall) -> None:
        """Handle print QR code service call."""
        entry_id = _get_entry_id(call)
        if not entry_id:
            return
        qr_content = call.data.get(ATTR_QR_CONTENT, "")
        qr_size = call.data.get(ATTR_QR_SIZE, 500)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)
        await hass.async_add_executor_job(
            _do_print_qr, entry_id, qr_content, qr_size, heat_density
        )

    async def handle_print_pickup_code(call: ServiceCall) -> None:
        """Handle print pickup code service call."""
        entry_id = _get_entry_id(call)
        if not entry_id:
            return
        pickup_code = call.data.get(ATTR_PICKUP_CODE, "")
        await hass.async_add_executor_job(_do_print_pickup_code, entry_id, pickup_code)

    async def handle_get_status(_call: ServiceCall) -> None:
        """Handle get status service call."""
        entry_id = _get_entry_id(_call)
        if not entry_id:
            return
        result = await hass.async_add_executor_job(_do_get_status, entry_id)
        _LOGGER.info("Paperang P2 status: %s", result)

    async def handle_feed_paper(call: ServiceCall) -> None:
        """Handle feed paper service call."""
        entry_id = _get_entry_id(call)
        if not entry_id:
            return
        lines = call.data.get(ATTR_LINES, 100)
        await hass.async_add_executor_job(_do_feed_paper, entry_id, lines)

    async def handle_print_test_page(_call: ServiceCall) -> None:
        """Handle print test page service call."""
        entry_id = _get_entry_id(_call)
        if not entry_id:
            return
        await hass.async_add_executor_job(_do_print_test_page, entry_id)

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_PRINT_TEXT, handle_print_text)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_IMAGE, handle_print_image)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_QR, handle_print_qr)
    hass.services.async_register(
        DOMAIN, SERVICE_PRINT_PICKUP_CODE, handle_print_pickup_code
    )
    hass.services.async_register(DOMAIN, SERVICE_GET_STATUS, handle_get_status)
    hass.services.async_register(DOMAIN, SERVICE_FEED_PAPER, handle_feed_paper)
    hass.services.async_register(
        DOMAIN, SERVICE_PRINT_TEST_PAGE, handle_print_test_page
    )

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
            entry,
            data=data,
            version=2,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up from config entry (also called after YAML import)."""
    _transport_configs[entry.entry_id] = dict(entry.data)

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
    _transport_configs.pop(entry.entry_id, None)
    _static_caches.pop(entry.entry_id, None)
    _dynamic_caches.pop(entry.entry_id, None)
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
