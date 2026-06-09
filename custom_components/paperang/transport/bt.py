"""Classic Bluetooth (SPP/RFCOMM) device scan and verification.

Paperang P2 uses BR/EDR classic Bluetooth (SPP), not BLE.
Scan wraps ``bluetoothctl``; verify uses ``BtTransport`` from paperang-p2-lib>=1.1.0.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

from typing import Any

from ..core.paperang_lib import BtTransport, PaperangP2

BT_NAMES = {"paperang", "miaomiaoji"}


def _scan_fallback_devices(seen: set[str]) -> list[dict[str, Any]]:
    """Fallback: bluetoothctl devices for already-paired printers."""
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
                    if addr not in seen and any(
                        name.lower().startswith(n) for n in BT_NAMES
                    ):
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
        if name and any(name.lower().startswith(n) for n in BT_NAMES):
            result.append({"name": name, "address": addr})
            seen.add(addr)

    # Fallback for already-paired
    if not result:
        result = _scan_fallback_devices(seen)

    return result


def verify_bt_printer(address: str) -> bool:
    """Connect to classic-BT printer and verify communication.

    BtTransport is synchronous (pure socket) — no event-loop is needed,
    unlike BleTransport which requires ``asyncio.run_until_complete()``.

    Returns True on success, False on any error.
    """
    if BtTransport is None:
        return False

    printer = None
    try:
        printer = PaperangP2(transport=BtTransport(address=address))
        printer.connect()
        battery = printer.get_battery()
        return battery is not None
    except Exception:  # pylint: disable=broad-exception-caught
        return False
    finally:
        if printer is not None:
            try:
                printer.disconnect()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
