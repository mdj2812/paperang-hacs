"""USB transport, device enumeration, and config-flow verification."""
# pylint: disable=duplicate-code,too-few-public-methods

from __future__ import annotations

import time

from typing import Any

from ..core.paperang_lib import (
    PaperangP2,
    UsbTransportBase,
    resolve_model,
    usb_pids,
)

PAPERANG_VID = 0x4348
PAPERANG_PID = 0x5584


def _registered_pids() -> tuple[int, ...]:
    """Every product ID the installed library knows about, P2 first."""
    if usb_pids is None:
        return (PAPERANG_PID,)
    try:
        pids = tuple(usb_pids())
    except Exception:  # pylint: disable=broad-exception-caught
        return (PAPERANG_PID,)
    if not pids:
        return (PAPERANG_PID,)
    # Keep the P2 first so the primary PID stays what it always was.
    return (PAPERANG_PID,) + tuple(p for p in pids if p != PAPERANG_PID)


PAPERANG_PIDS = _registered_pids()


class UsbTransportWithPath(UsbTransportBase):
    """UsbTransport that connects to a specific device by bus/port.

    The default *UsbTransport* always picks the first matching VID/PID
    device.  This subclass lets us pin a specific physical printer when
    multiple are attached.
    """

    def __init__(self, bus, port, vid=PAPERANG_VID, pid=None, pids=None):
        """Pin one physical device by bus/port.

        Without an explicit ``pid`` every registered model's product ID is
        searched, so the same code path works for a P2 and a D1.
        """
        if pids is None:
            pids = (pid,) if pid is not None else PAPERANG_PIDS
        super().__init__(vid, pid, pids)
        self._target_bus = bus
        self._target_port = tuple(port) if port else ()
        # Kept locally rather than read back off the parent, so this subclass
        # does not depend on the parent's attribute bookkeeping.
        self._pids = tuple(pids)
        self.matched_pid = None
        self._dev = None
        self._ep_out = None
        self._ep_in = None

    def connect(self):
        """Find the targeted USB device, claim and configure it."""
        import usb.core  # pylint: disable=import-outside-toplevel
        import usb.util  # pylint: disable=import-outside-toplevel

        self._dev = None
        self.matched_pid = None
        for pid in self._pids:
            devices = usb.core.find(find_all=True, idVendor=self.vid, idProduct=pid)
            for d in devices:
                if (
                    d.bus == self._target_bus
                    and tuple(d.port_numbers) == self._target_port
                ):
                    self._dev = d
                    self.matched_pid = pid
                    break
            if self._dev is not None:
                break

        if self._dev is None:
            wanted = "/".join(f"0x{pid:04x}" for pid in self._pids)
            raise RuntimeError(
                f"Paperang printer not found at bus={self._target_bus} "
                f"port={list(self._target_port)} (PID {wanted})"
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
    """Return every attached Paperang USB device, across known models.

    Each dict: ``usb_path`` (display string), ``bus``, ``port``, ``address``,
    ``pid`` and ``model`` (the model name when the PID maps to exactly one
    registered model, otherwise None).
    Returns empty list if pyusb is missing or no devices found.
    """
    try:
        import usb.core  # pylint: disable=import-outside-toplevel
    except ImportError:
        return []

    result: list[dict[str, Any]] = []
    for pid in PAPERANG_PIDS:
        devices = usb.core.find(find_all=True, idVendor=PAPERANG_VID, idProduct=pid)
        for dev in devices:
            port = list(dev.port_numbers) if dev.port_numbers else []
            usb_path = "-".join(str(p) for p in [dev.bus] + port)
            result.append(
                {
                    "usb_path": usb_path,
                    "bus": dev.bus,
                    "port": port,
                    "address": dev.address,
                    "pid": pid,
                    "model": _model_for_pid(pid),
                }
            )
    return result


def _model_for_pid(pid: int) -> str | None:
    """Model name for a USB product ID, when it identifies one model."""
    if usb_pids is None or resolve_model is None:
        return None
    try:
        matches = {model.name for model in _models_matching_pid(pid)}
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    return matches.pop() if len(matches) == 1 else None


def _models_matching_pid(pid: int):
    """Registered models whose product IDs include *pid*."""
    from ..core.paperang_lib import list_models  # pylint: disable=import-outside-toplevel

    if list_models is None:
        return ()
    return [
        model for model in list_models().values() if pid in getattr(model, "pids", ())
    ]


def probe_usb_printer(bus: int, port: list[int]) -> dict[str, Any]:
    """Connect to the device, read the battery, and resolve its model.

    Retries on USB Resource busy errors caused by concurrent access.
    Returns ``{"available": bool, "model": str | None}``.
    """
    for _ in range(3):
        printer = None
        transport = None
        try:
            transport = UsbTransportWithPath(bus=bus, port=port)
            printer = PaperangP2(transport=transport)
            printer.connect()
            battery = printer.get_battery()
            available = battery is not None
            return {
                "available": available,
                "model": _resolve_model_name(transport, printer) if available else None,
            }
        except Exception as err:  # pylint: disable=broad-exception-caught
            if "Resource busy" in str(err) or "Entity" in str(err):
                time.sleep(0.5)
                continue
            return {"available": False, "model": None}
        finally:
            if printer is not None:
                try:
                    printer.disconnect()
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
    return {"available": False, "model": None}


def _resolve_model_name(transport, printer) -> str | None:
    """Model name reported by a connected printer, or None."""
    if resolve_model is None:
        return None
    try:
        model = resolve_model(
            vid=getattr(transport, "vid", None),
            pid=getattr(transport, "matched_pid", None),
            reported_name=printer.get_model(),
        )
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    return getattr(model, "name", None)


def verify_printer(bus: int, port: list[int]) -> bool:
    """Backwards-compatible boolean check used by older callers."""
    return probe_usb_printer(bus, port)["available"]
