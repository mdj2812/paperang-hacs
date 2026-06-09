"""Per-config-entry transport wiring and :class:`PaperangP2` factory."""

from __future__ import annotations

from ..const import (
    CONF_BT_ADDRESS,
    CONF_BLE_ADDRESS,
    CONF_TRANSPORT,
    CONF_USB_BUS,
    CONF_USB_PORT,
    TRANSPORT_BT,
    TRANSPORT_BLE,
)
from ..transport.usb import UsbTransportWithPath
from .paperang_lib import BtTransport, BleTransport, PaperangP2

transport_configs: dict[str, dict[str, object]] = {}


class _PersistentPrinterCache:
    """Cache of connected printers (USB + BT SPP), keyed by entry_id.

    USB and BT printers are cached after the first successful connect.
    Subsequent calls reuse the same transport to avoid USB ``Resource
    busy`` errors and duplicate RFCOMM sockets.

    BLE printers are intentionally excluded — BLE connections are
    short-lived and managed separately.
    """

    def __init__(self) -> None:
        self._printers: dict[str, object] = {}

    def get_or_create(self, entry_id: str) -> object:
        """Return a cached (already connected) printer, or create + connect."""
        cfg = transport_configs.get(entry_id, {})
        if cfg.get(CONF_TRANSPORT) == TRANSPORT_BLE:
            return None  # type: ignore[return-value]

        if entry_id in self._printers:
            return self._printers[entry_id]

        printer = _get_printer(entry_id)
        printer.connect()
        self._printers[entry_id] = printer
        return printer

    def cache(self, entry_id: str, printer: object) -> None:
        """Store a connected printer for reuse."""
        self._printers[entry_id] = printer

    def pop(self, entry_id: str) -> object | None:
        """Remove and return a cached printer (e.g. on connection loss)."""
        return self._printers.pop(entry_id, None)

    def clear(self) -> None:
        """Remove all cached printers."""
        self._printers.clear()


_persistent_printers = _PersistentPrinterCache()


# Public API — thin wrappers around the cache instance.
# (Kept as module-level functions for backward compat with callers.)

def _get_or_reuse_printer(entry_id: str):
    """Return a persistent printer if available (USB/BT); None for BLE."""
    return _persistent_printers.get_or_create(entry_id)


def _cache_printer(entry_id: str, printer: object) -> None:
    """Cache a printer for persistent reuse (USB or BT)."""
    _persistent_printers.cache(entry_id, printer)


def _pop_printer(entry_id: str) -> object | None:
    """Remove and return a cached persistent printer."""
    return _persistent_printers.pop(entry_id)


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
    if transport_type == TRANSPORT_BT and BtTransport is not None:
        bt_addr = cfg.get(CONF_BT_ADDRESS, "")
        bt = BtTransport(address=bt_addr) if bt_addr else BtTransport()
        return PaperangP2(transport=bt)

    if transport_type == TRANSPORT_BLE and BleTransport is not None:
        ble_addr = cfg.get(CONF_BLE_ADDRESS, "")
        ble = BleTransport(address=ble_addr) if ble_addr else BleTransport()
        return PaperangP2(transport=ble)

    bus = cfg.get(CONF_USB_BUS)
    port = cfg.get(CONF_USB_PORT)
    if bus is not None and port is not None:
        return PaperangP2(transport=UsbTransportWithPath(bus=bus, port=port))

    return PaperangP2()
