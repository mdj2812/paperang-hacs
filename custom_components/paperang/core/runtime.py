"""Per-config-entry transport wiring and :class:`PaperangP2` factory."""

from __future__ import annotations

import threading

from ..const import (
    CONF_BLE_ADDRESS,
    CONF_TRANSPORT,
    CONF_USB_BUS,
    CONF_USB_PORT,
    TRANSPORT_BLE,
)
from .paperang_lib import BleTransport, PaperangP2
from ..transport.usb import UsbTransportWithPath

transport_configs: dict[str, dict[str, object]] = {}

# Per-entry thread lock to prevent concurrent USB access
# (coordinator polling and service calls share the same USB device)
_usb_locks: dict[str, threading.Lock] = {}


def _get_usb_lock(entry_id: str) -> threading.Lock:
    """Get or create a per-entry USB lock."""
    if entry_id not in _usb_locks:
        _usb_locks[entry_id] = threading.Lock()
    return _usb_locks[entry_id]


def _clear_usb_lock(entry_id: str) -> None:
    """Remove the USB lock for an entry (on unload)."""
    _usb_locks.pop(entry_id, None)


def _get_printer(entry_id: str | None = None):
    """Create a PaperangP2 with the configured transport.

    When *entry_id* is given the matching config entry is used;
    otherwise the first configured entry is returned.
    """
    if entry_id and entry_id in transport_configs:
        cfg = transport_configs[entry_id]
    elif transport_configs:
        entry_id, cfg = next(iter(transport_configs.items()))
    else:
        return PaperangP2()

    transport_type = cfg.get(CONF_TRANSPORT, "")
    if transport_type == TRANSPORT_BLE and BleTransport is not None:
        ble_addr = cfg.get(CONF_BLE_ADDRESS, "")
        ble = BleTransport(address=ble_addr) if ble_addr else BleTransport()
        return PaperangP2(transport=ble)

    bus = cfg.get(CONF_USB_BUS)
    port = cfg.get(CONF_USB_PORT)
    if bus is not None and port is not None:
        return PaperangP2(transport=UsbTransportWithPath(bus=bus, port=port))

    return PaperangP2()
