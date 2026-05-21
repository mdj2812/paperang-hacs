"""Blocking printer operations (connect → work → disconnect)."""

from __future__ import annotations

import time

from .runtime import _get_printer


def _with_printer(entry_id: str, fn):
    """Create a printer, connect, run *fn(printer)*, disconnect.

    Retries on USB Resource busy errors caused by concurrent access
    (coordinator polling and service calls competing for the device).
    """
    last_err = None
    for _ in range(3):
        printer = _get_printer(entry_id)
        try:
            printer.connect()
            return fn(printer)
        except Exception as err:
            last_err = err
            if "Resource busy" in str(err) or "Entity" in str(err):
                time.sleep(0.5)
                continue
            raise
        finally:
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
