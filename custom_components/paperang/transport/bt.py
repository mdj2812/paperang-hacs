"""Classic Bluetooth (SPP/RFCOMM) device scan and verification.

Paperang P2 uses BR/EDR classic Bluetooth (SPP), not BLE.
Scan wraps ``bluetoothctl``; verify uses ``BtTransport`` from paperang-p2-lib>=1.1.0.
"""

from __future__ import annotations

from typing import Any

from ..core.paperang_lib import BtTransport, PaperangP2

BT_NAMES = {"paperang", "miaomiaoji"}


def scan_bt_devices() -> list[dict[str, Any]]:
    """Scan for nearby Paperang classic-BT devices.

    Each dict: ``name``, ``address``.
    Returns empty list if BtTransport is unavailable or no devices found.
    """
    if BtTransport is None:
        return []

    try:
        devices = BtTransport.scan()
    except Exception:  # pylint: disable=broad-exception-caught
        return []

    result: list[dict[str, Any]] = []
    for addr, name in devices:
        if name and any(name.lower().startswith(n) for n in BT_NAMES):
            result.append({"name": name, "address": addr})
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
