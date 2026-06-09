"""Blocking / async printer telemetry reads and per-entry caches."""

from __future__ import annotations

import logging
import time

from homeassistant.core import HomeAssistant

from ..const import CONF_TRANSPORT, TRANSPORT_BLE, TRANSPORT_BT
from .blocking import _get_lock
from .runtime import (
    _cache_bt_printer,
    _get_or_reuse_printer,
    _get_printer,
    _pop_bt_printer,
    transport_configs,
)

_LOGGER = logging.getLogger(__name__)

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


def _update_if_not_none(cache: dict[str, object], key: str, val: object) -> None:
    """Update cache if value is not None, otherwise keep existing."""
    if val is not None:
        cache[key] = val


def _get_or_fallback(cache: dict[str, object], key: str) -> object:
    """Get value from cache, return None if never seen."""
    return cache.get(key)


def clear_caches_for_entry(entry_id: str) -> None:
    """Remove cached telemetry and persistent printer for a config entry."""
    _static_caches.pop(entry_id, None)
    _dynamic_caches.pop(entry_id, None)
    bt_printer = _pop_bt_printer(entry_id)
    if bt_printer is not None:
        try:
            bt_printer.disconnect()
        except Exception:  # pylint: disable=broad-exception-caught
            pass


async def _read_printer_state(hass: HomeAssistant, entry_id: str):
    """Read all printer telemetry.

    USB: blocking I/O in executor thread — connect/read/disconnect each poll.
    BT (classic SPP): blocking I/O with persistent RFCOMM connection.
    BLE: skip polling — BLE only connects during on-demand operations.
    """
    cfg = transport_configs.get(entry_id, {})
    if cfg.get(CONF_TRANSPORT) == TRANSPORT_BLE:
        return {"available": True, "connected": "connected"}
    return await hass.async_add_executor_job(_blocking_read_printer_state, entry_id)


def _blocking_read_printer_state(entry_id: str):  # noqa: C901
    # pylint: disable=too-many-locals
    """Blocking: connect to printer and read telemetry.

    Dynamic values (battery, status): read every poll.  If None, keep
    the last known value so gaps don't show as unavailable.

    Static values (voltage, temperature, firmware, etc.): read every
    poll until a non-None value is obtained; thereafter reuse cache.

    BT (classic SPP): keeps the RFCOMM connection open across polls.
    Reconnects only on failure.

    Retries up to 3 times on failure; logs warning if all fail.
    """
    cfg = transport_configs.get(entry_id, {})
    is_bt = cfg.get(CONF_TRANSPORT) == TRANSPORT_BT

    for attempt in range(1, _RETRIES + 1):
        data: dict[str, object] = {"available": False}
        static_cache = _get_static_cache(entry_id)
        dynamic_cache = _get_dynamic_cache(entry_id)

        # ── Get or reuse persistent BT printer ──
        if is_bt and entry_id in _bt_persistent_printers:
            printer = _get_or_reuse_printer(entry_id)

        # Serialize USB/BT access with print services
        lock = _get_lock(entry_id)
        try:
            with lock:
                # Only connect if not already connected (BT persistent)
                if not is_bt:
                    printer.connect()

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

                for key, reader in _STATIC_READERS:
                    time.sleep(0.05)
                    val = reader(printer)
                    if key == "version" and val is not None:
                        try:
                            ver_int = int(val)
                            val = (
                                f"V{ver_int & 0xFF}."
                                f"{(ver_int >> 8) & 0xFF}."
                                f"{(ver_int >> 16) & 0xFFFF}"
                            )
                        except (ValueError, TypeError):
                            pass
                    _update_if_not_none(static_cache, key, val)

                for key in _STATIC_KEYS:
                    data[key] = _get_or_fallback(static_cache, key)
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
                data["connected"] = "connected"
                # Cache the connected printer for reuse
                if is_bt:
                    _cache_bt_printer(entry_id, printer)
                return data
        except Exception as err:  # pylint: disable=broad-exception-caught
            # Connection lost — clear cached printer so next poll reconnects
            if is_bt:
                _pop_bt_printer(entry_id)
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
                clear_caches_for_entry(entry_id)
        finally:
            # Only disconnect if NOT using persistent connection
            if not is_bt:
                printer.disconnect()

    return {"available": False, "connected": "disconnected"}
