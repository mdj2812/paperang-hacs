"""Blocking / async printer telemetry reads and per-entry caches."""
# pylint: disable=protected-access

from __future__ import annotations

import logging
import time

from homeassistant.core import HomeAssistant

from ..const import CONF_TRANSPORT, TRANSPORT_BLE, TRANSPORT_BT
from . import runtime as _rt
from .blocking import _get_lock

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
    bt_printer = _rt._pop_bt_printer(entry_id)
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
    cfg = _rt.transport_configs.get(entry_id, {})
    if cfg.get(CONF_TRANSPORT) == TRANSPORT_BLE:
        return {"available": True, "connected": "connected"}
    return await hass.async_add_executor_job(_blocking_read_printer_state, entry_id)


def _format_version(val: object) -> str | None:
    """Format raw version integer as Vx.y.z string.

    Returns formatted string on success, None if val is None,
    or the original value if it cannot be parsed as an integer.
    """
    if val is None:
        return None
    try:
        ver_int = int(val)
        return (
            f"V{ver_int & 0xFF}."
            f"{(ver_int >> 8) & 0xFF}."
            f"{(ver_int >> 16) & 0xFFFF}"
        )
    except (ValueError, TypeError):
        return str(val)


def _read_dynamic(
    printer: object,
    dynamic_cache: dict[str, object],
) -> dict[str, object]:
    """Read battery + status, applying cache fallback."""
    battery = printer.get_battery()
    time.sleep(0.05)
    status = printer.get_status()

    data: dict[str, object] = {
        "battery": battery if battery is not None
        else _get_or_fallback(dynamic_cache, "battery"),
        "status": status if status is not None
        else _get_or_fallback(dynamic_cache, "status"),
    }
    _update_if_not_none(dynamic_cache, "battery", battery)
    _update_if_not_none(dynamic_cache, "status", status)
    return data


def _read_static(
    printer: object,
    static_cache: dict[str, object],
) -> dict[str, object]:
    """Read all static telemetry values, skipping already-cached keys."""
    data: dict[str, object] = {}
    for key, reader in _STATIC_READERS:
        if key in static_cache:
            data[key] = static_cache[key]
            continue
        time.sleep(0.05)
        val = reader(printer)
        if key == "version":
            val = _format_version(val)
        _update_if_not_none(static_cache, key, val)
        data[key] = _get_or_fallback(static_cache, key)
    return data


def _try_read_once(
    entry_id: str,
    is_bt: bool,
    static_cache: dict[str, object],
    dynamic_cache: dict[str, object],
) -> dict[str, object]:
    """Attempt a single connect/read/disconnect cycle.

    Returns telemetry data dict.  Raises on any error (caller handles retries).
    """
    printer: object
    if is_bt:
        printer = _rt._get_or_reuse_printer(entry_id)
    else:
        printer = _rt._get_printer(entry_id)

    data: dict[str, object] = {"available": False}
    lock = _get_lock(entry_id)
    try:
        with lock:
            if not is_bt:
                printer.connect()

            data.update(_read_dynamic(printer, dynamic_cache))
            data.update(_read_static(printer, static_cache))

            ver = data.get("version")
            if ver is not None:
                formatted = _format_version(ver)
                if formatted is not None:
                    data["version"] = formatted

            data["available"] = True
            data["connected"] = "connected"
            if is_bt:
                _rt._cache_bt_printer(entry_id, printer)
            return data
    finally:
        if not is_bt:
            printer.disconnect()


def _blocking_read_printer_state(entry_id: str):
    """Blocking: connect to printer and read telemetry.

    Dynamic values (battery, status): read every poll.  If None, keep
    the last known value so gaps don't show as unavailable.

    Static values (voltage, temperature, firmware, etc.): read every
    poll until a non-None value is obtained; thereafter reuse cache.

    BT (classic SPP): keeps the RFCOMM connection open across polls.
    Reconnects only on failure.

    Retries up to 3 times on failure; logs warning if all fail.
    """
    cfg = _rt.transport_configs.get(entry_id, {})
    is_bt = cfg.get(CONF_TRANSPORT) == TRANSPORT_BT
    static_cache = _get_static_cache(entry_id)
    dynamic_cache = _get_dynamic_cache(entry_id)

    for attempt in range(1, _RETRIES + 1):
        try:
            return _try_read_once(entry_id, is_bt, static_cache, dynamic_cache)
        except Exception as err:  # pylint: disable=broad-exception-caught
            if is_bt:
                _rt._pop_bt_printer(entry_id)
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
                clear_caches_for_entry(entry_id)

    return {"available": False, "connected": "disconnected"}
