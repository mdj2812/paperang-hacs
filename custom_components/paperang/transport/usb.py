"""USB transport, device enumeration, and config-flow verification."""

from __future__ import annotations

from typing import Any

from ..core.paperang_lib import PaperangP2, UsbTransportBase

PAPERANG_VID = 0x4348
PAPERANG_PID = 0x5584


class UsbTransportWithPath(UsbTransportBase):
    """UsbTransport that connects to a specific device by bus/port.

    The default *UsbTransport* always picks the first matching VID/PID
    device.  This subclass lets us pin a specific physical printer when
    multiple are attached.
    """

    def __init__(self, bus, port, vid=0x4348, pid=0x5584):
        super().__init__(vid, pid)
        self._target_bus = bus
        self._target_port = tuple(port) if port else ()

    def connect(self):
        """Find the targeted USB device, claim and configure it."""
        import usb.core  # pylint: disable=import-outside-toplevel
        import usb.util  # pylint: disable=import-outside-toplevel

        devices = usb.core.find(find_all=True, idVendor=self.vid, idProduct=self.pid)
        self._dev = None
        for d in devices:
            if d.bus == self._target_bus and tuple(d.port_numbers) == self._target_port:
                self._dev = d
                break

        if self._dev is None:
            raise RuntimeError(
                f"Paperang P2 not found at bus={self._target_bus} "
                f"port={list(self._target_port)}"
            )

        if self._dev.is_kernel_driver_active(0):
            self._dev.detach_kernel_driver(0)
        self._dev.set_configuration()
        cfg = self._dev.get_active_configuration()
        intf = cfg[(0, 0)]
        self._ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            ),
        )
        self._ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            ),
        )
        return True


def scan_usb_devices() -> list[dict[str, Any]]:
    """Return all Paperang P2 USB devices currently attached.

    Each dict: ``usb_path`` (display string), ``bus``, ``port``,
    ``address``.
    Returns empty list if pyusb is missing or no devices found.
    """
    try:
        import usb.core  # pylint: disable=import-outside-toplevel
    except ImportError:
        return []

    devices = usb.core.find(
        find_all=True, idVendor=PAPERANG_VID, idProduct=PAPERANG_PID
    )
    result: list[dict[str, Any]] = []
    for dev in devices:
        port = list(dev.port_numbers) if dev.port_numbers else []
        usb_path = "-".join(str(p) for p in [dev.bus] + port)
        result.append(
            {
                "usb_path": usb_path,
                "bus": dev.bus,
                "port": port,
                "address": dev.address,
            }
        )
    return result


def verify_printer(bus: int, port: list[int]) -> bool:
    """Quick check: connect to the device and read battery.

    Returns True on success, False on any error.
    """
    printer = None
    try:
        printer = PaperangP2(transport=UsbTransportWithPath(bus=bus, port=port))
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
