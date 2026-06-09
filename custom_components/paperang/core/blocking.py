"""Blocking printer operations (connect → work → disconnect)."""

from __future__ import annotations

import threading
import time

from .runtime import _cache_bt_printer, _get_or_reuse_printer, _get_printer, _pop_bt_printer

# Per-entry locks to serialize USB access between coordinator polling
# and on-demand print services.
_locks: dict[str, threading.Lock] = {}


def _get_lock(entry_id: str) -> threading.Lock:
    if entry_id not in _locks:
        _locks[entry_id] = threading.Lock()
    return _locks[entry_id]


def _with_printer(entry_id: str, fn):
    """Create a printer, connect, run *fn(printer)*, disconnect.

    Uses a per-entry lock to serialize USB/BT access between coordinator
    polling and on-demand print service calls.  Retries on USB Resource
    busy errors caused by kernel driver conflicts.

    For BT transport: reuses the persistent RFCOMM connection to avoid
    ``[Errno 16] Resource busy`` from duplicate socket opens.
    """
    lock = _get_lock(entry_id)
    last_err = None

    # Check if a persistent BT printer exists — reuse to avoid duplicate socket
    cached = _get_or_reuse_printer(entry_id)
    already_connected = cached is not None

    for _ in range(3):
        with lock:
            printer = cached if cached is not None else _get_printer(entry_id)
            try:
                if not already_connected:
                    printer.connect()
                return fn(printer)
            except Exception as err:
                last_err = err
                # On BT failure, clear cached printer so next call reconnects
                _pop_bt_printer(entry_id)
                cached = None
                already_connected = False
                if "Resource busy" in str(err) or "Entity" in str(err):
                    time.sleep(0.5)
                    continue
                raise
            finally:
                if not already_connected:
                    printer.disconnect()
    raise last_err  # pylint: disable=raising-bad-type


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
