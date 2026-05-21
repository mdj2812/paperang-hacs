"""BLE device scan and verification for the config flow."""

from __future__ import annotations

from typing import Any

from ..core.paperang_lib import BleTransport, PaperangP2

BLE_NAMES = {"paperang", "miaomiaoji"}


async def async_scan_ble_devices() -> list[dict[str, Any]]:
    """Scan for nearby Paperang BLE devices.

    Each dict: ``name``, ``address``.
    """
    try:
        from bleak import BleakScanner  # pylint: disable=import-outside-toplevel
    except ImportError:
        return []

    try:
        devices = await BleakScanner.discover(timeout=5)
    except Exception:  # pylint: disable=broad-exception-caught
        return []

    result: list[dict[str, Any]] = []
    for d in devices:
        if d.name and any(d.name.lower().startswith(n) for n in BLE_NAMES):
            result.append({"name": d.name, "address": d.address})
    return result


async def async_verify_ble_printer(address: str) -> bool:
    """Connect to BLE printer and verify communication."""
    if BleTransport is None:
        return False

    printer = None
    try:
        printer = PaperangP2(transport=BleTransport(address=address))
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
