"""Classic Bluetooth (SPP/RFCOMM) device scan and verification.

Paperang P2 uses BR/EDR classic Bluetooth (SPP), not BLE.
Scan wraps ``bluetoothctl``; verify uses ``BtTransport`` from paperang-p2-lib>=1.1.0.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

from typing import Any

from ..core.paperang_lib import (
    BtTransport,
    PAPERANG_BT_NAMES,
    PaperangP2,
    check_paperang_uuid,
    resolve_model,
)


def _scan_fallback_devices(seen: set[str]) -> list[dict[str, Any]]:
    """Fallback: bluetoothctl devices for already-paired printers.

    Discovery strategy:
    1. Name starts with paperang/miaomiaoji → fast path accept
    2. Otherwise → bluetoothctl info <addr>, check for 0000fee7 UUID

    This ensures renamed/paired printers are discoverable by their
    SDP service UUID even if the reported device name is non-standard.
    """
    import subprocess  # pylint: disable=import-outside-toplevel

    result: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("Device "):
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    addr, name = parts[1], parts[2]
                    if addr in seen:
                        continue
                    if any(name.lower().startswith(n) for n in PAPERANG_BT_NAMES):
                        result.append({"name": name, "address": addr})
                        seen.add(addr)
                    elif check_paperang_uuid(addr):
                        result.append({"name": name, "address": addr})
                        seen.add(addr)
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return result


def scan_bt_devices() -> list[dict[str, Any]]:
    """Scan for nearby Paperang classic-BT devices.

    Uses ``BtTransport.scan()`` (active discovery), falling back to
    ``_scan_fallback_devices`` for already-paired printers.
    """
    if BtTransport is None:
        return []

    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Active scan via BtTransport
    try:
        devices = BtTransport.scan()
    except Exception:  # pylint: disable=broad-exception-caught
        devices = []

    for addr, name in devices:
        if name and any(name.lower().startswith(n) for n in PAPERANG_BT_NAMES):
            result.append({"name": name, "address": addr})
            seen.add(addr)

    # Fallback for already-paired
    if not result:
        result = _scan_fallback_devices(seen)

    return result


def verify_bt_printer(address: str) -> bool:
    """Backwards-compatible boolean check used by older callers."""
    return probe_bt_printer(address)["available"]


def probe_bt_printer(address: str) -> dict[str, Any]:
    """Connect to a classic-BT printer, verify it, and resolve its model.

    ``BtTransport`` is synchronous (a plain RFCOMM socket), so no event loop is
    involved.  Returns ``{"available": bool, "model": str | None}``; the model
    comes from ``CMD_GET_MODEL``, since Bluetooth carries no VID/PID.
    """
    if BtTransport is None:
        return {"available": False, "model": None}

    printer = None
    transport = None
    try:
        transport = BtTransport(address=address)
        printer = PaperangP2(transport=transport)
        printer.connect()
        battery = printer.get_battery()
        available = battery is not None
        model = None
        if available and resolve_model is not None:
            try:
                model = resolve_model(reported_name=printer.get_model()).name
            except Exception:  # pylint: disable=broad-exception-caught
                model = None
        return {"available": available, "model": model}
    except Exception:  # pylint: disable=broad-exception-caught
        return {"available": False, "model": None}
    finally:
        if printer is not None:
            try:
                printer.disconnect()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
