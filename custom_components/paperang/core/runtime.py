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
from .paperang_lib import BtTransport, BleTransport, PaperangP2
from ..transport.usb import UsbTransportWithPath

transport_configs: dict[str, dict[str, object]] = {}


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
