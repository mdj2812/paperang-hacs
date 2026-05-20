# pylint: disable=import-error
"""Config flow for Paperang P2 Printer integration.

USB / BLE discovery scans for all compatible devices and lets the user
pick one.  Each device is identified by USB bus+port path or BLE address
so multiple printers can coexist.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_BLE_ADDRESS,
    CONF_TRANSPORT,
    CONF_USB_BUS,
    CONF_USB_PORT,
    DOMAIN,
    TRANSPORT_BLE,
    TRANSPORT_USB,
)

# ── USB discovery helpers ────────────────────────────────────────

PAPERANG_VID = 0x4348
PAPERANG_PID = 0x5584


def _scan_usb_devices() -> list[dict[str, Any]]:
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


def _verify_printer(bus: int, port: list[int]) -> bool:
    """Quick check: connect to the device and read battery.

    Returns True on success, False on any error.
    """
    try:
        import paperang  # pylint: disable=import-outside-toplevel
    except ImportError:
        return False

    from . import UsbTransportWithPath  # pylint: disable=import-outside-toplevel

    printer = paperang.PaperangP2(transport=UsbTransportWithPath(bus=bus, port=port))
    try:
        printer.connect()
        battery = printer.get_battery()
        return battery is not None
    except Exception:  # pylint: disable=broad-exception-caught
        return False
    finally:
        try:
            printer.disconnect()
        except Exception:  # pylint: disable=broad-exception-caught
            pass


# ── BLE discovery helpers ────────────────────────────────────────

BLE_NAMES = {"paperang", "miaomiaoji"}


async def _async_scan_ble_devices() -> list[dict[str, Any]]:
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


async def _async_verify_ble_printer(address: str) -> bool:
    """Connect to BLE printer and verify communication."""
    try:
        import paperang  # pylint: disable=import-outside-toplevel
        from paperang.transport import (  # pylint: disable=import-outside-toplevel
            BleTransport,
        )
    except ImportError:
        return False

    printer = paperang.PaperangP2(transport=BleTransport(address=address))
    try:
        printer.connect()
        battery = printer.get_battery()
        return battery is not None
    except Exception:  # pylint: disable=broad-exception-caught
        return False
    finally:
        try:
            printer.disconnect()
        except Exception:  # pylint: disable=broad-exception-caught
            pass


# ── Config Flow ──────────────────────────────────────────────────


class PaperangConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Paperang P2 Printer."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise."""
        super().__init__()
        self._usb_discovered: list[dict[str, Any]] = []
        self._selected_usb: dict[str, Any] | None = None
        self._ble_discovered: list[dict[str, Any]] = []
        self._selected_ble: dict[str, Any] | None = None
        self._transport: str = TRANSPORT_USB

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return PaperangOptionsFlow(config_entry)

    # ── USB discovery ─────────────────────────────────────────

    async def async_step_usb(self, discovery_info=None):
        """Handle USB discovery — scan for Paperang devices."""
        # pylint: disable=unused-argument
        self._transport = TRANSPORT_USB
        self._usb_discovered = await self.hass.async_add_executor_job(_scan_usb_devices)

        if not self._usb_discovered:
            return self.async_abort(reason="no_usb_device_found")

        if len(self._usb_discovered) == 1:
            self._selected_usb = self._usb_discovered[0]
            return await self.async_step_usb_verify()

        return await self.async_step_select_device()

    async def async_step_select_device(self, user_input: dict[str, Any] | None = None):
        """Let the user pick which USB device to use."""
        errors: dict[str, str] = {}

        if user_input is not None:
            chosen_path = user_input["usb_device"]
            for dev in self._usb_discovered:
                if dev["usb_path"] == chosen_path:
                    self._selected_usb = dev
                    break
            if self._selected_usb is None:
                errors["usb_device"] = "device_not_found"
            else:
                return await self.async_step_usb_verify()

        options = {
            dev["usb_path"]: (
                f"Paperang P2 — USB {dev['usb_path']}"
                f" (bus {dev['bus']}, addr {dev['address']})"
            )
            for dev in self._usb_discovered
        }

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({vol.Required("usb_device"): vol.In(options)}),
            errors=errors,
        )

    async def async_step_usb_verify(
        self,
        user_input: dict[str, Any] | None = None,  # pylint: disable=unused-argument
    ):
        """Verify communication with the selected USB device."""
        if self._selected_usb is None:
            return self.async_abort(reason="no_usb_device_found")

        dev = self._selected_usb
        usb_path = dev["usb_path"]

        await self.async_set_unique_id(f"paperang_usb_{usb_path}")
        self._abort_if_unique_id_configured()

        ok = await self.hass.async_add_executor_job(
            _verify_printer, dev["bus"], dev["port"]
        )

        if not ok:
            return self.async_show_form(
                step_id="usb_verify",
                errors={"base": "communication_failed"},
            )

        return self.async_create_entry(
            title=f"Paperang P2 (USB {usb_path})",
            data={
                CONF_TRANSPORT: TRANSPORT_USB,
                CONF_USB_BUS: dev["bus"],
                CONF_USB_PORT: dev["port"],
            },
        )

    # ── BLE discovery ─────────────────────────────────────────

    async def async_step_bluetooth(self, discovery_info):
        """Handle Bluetooth discovery — scan for BLE devices."""
        self._transport = TRANSPORT_BLE

        # Also accept HA's built-in Bluetooth discovery
        if hasattr(discovery_info, "address"):
            address = discovery_info.address
            name = getattr(discovery_info, "name", "Paperang P2")
            self._ble_discovered = [{"name": name, "address": address}]
        else:
            self._ble_discovered = await _async_scan_ble_devices()

        if not self._ble_discovered:
            return self.async_abort(reason="no_ble_device_found")

        if len(self._ble_discovered) == 1:
            self._selected_ble = self._ble_discovered[0]
            return await self.async_step_ble_verify()

        return await self.async_step_select_ble_device()

    async def async_step_select_ble_device(
        self, user_input: dict[str, Any] | None = None
    ):
        """Let the user pick which BLE device to use."""
        errors: dict[str, str] = {}

        if user_input is not None:
            chosen_addr = user_input["ble_device"]
            for dev in self._ble_discovered:
                if dev["address"] == chosen_addr:
                    self._selected_ble = dev
                    break
            if self._selected_ble is None:
                errors["ble_device"] = "device_not_found"
            else:
                return await self.async_step_ble_verify()

        options = {
            dev["address"]: f"{dev['name']} ({dev['address']})"
            for dev in self._ble_discovered
        }

        return self.async_show_form(
            step_id="select_ble_device",
            data_schema=vol.Schema({vol.Required("ble_device"): vol.In(options)}),
            errors=errors,
        )

    async def async_step_ble_verify(
        self,
        user_input: dict[str, Any] | None = None,  # pylint: disable=unused-argument
    ):
        """Verify communication with the selected BLE device."""
        if self._selected_ble is None:
            return self.async_abort(reason="no_ble_device_found")

        dev = self._selected_ble
        address = dev["address"]

        await self.async_set_unique_id(f"paperang_ble_{address}")
        self._abort_if_unique_id_configured()

        ok = await _async_verify_ble_printer(address)
        if not ok:
            return self.async_show_form(
                step_id="ble_verify",
                errors={"base": "communication_failed"},
            )

        return self.async_create_entry(
            title=f"Paperang P2 ({dev['name']})",
            data={
                CONF_TRANSPORT: TRANSPORT_BLE,
                CONF_BLE_ADDRESS: address,
            },
        )

    # ── Manual / import ────────────────────────────────────────

    @staticmethod
    def _user_schema():
        """Return the transport-selection schema (shared)."""
        return vol.Schema(
            {
                vol.Required(CONF_TRANSPORT, default=TRANSPORT_USB): vol.In(
                    {TRANSPORT_USB: "USB", TRANSPORT_BLE: "Bluetooth BLE"}
                ),
            }
        )

    async def _handle_usb_user_selection(self):
        """Handle USB path from async_step_user."""
        self._usb_discovered = await self.hass.async_add_executor_job(_scan_usb_devices)
        if not self._usb_discovered:
            return self.async_show_form(
                step_id="user",
                data_schema=self._user_schema(),
                errors={"base": "no_usb_device_found"},
            )
        if len(self._usb_discovered) == 1:
            self._selected_usb = self._usb_discovered[0]
            return await self.async_step_usb_verify()
        return await self.async_step_select_device()

    async def _handle_ble_user_selection(self):
        """Handle BLE path from async_step_user."""
        self._ble_discovered = await _async_scan_ble_devices()
        if not self._ble_discovered:
            return self.async_show_form(
                step_id="user",
                data_schema=self._user_schema(),
                errors={"base": "no_ble_device_found"},
            )
        if len(self._ble_discovered) == 1:
            self._selected_ble = self._ble_discovered[0]
            return await self.async_step_ble_verify()
        return await self.async_step_select_ble_device()

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step (manual add)."""
        if user_input is not None:
            transport = user_input[CONF_TRANSPORT]
            if transport == TRANSPORT_USB:
                return await self._handle_usb_user_selection()
            return await self._handle_ble_user_selection()
        return self.async_show_form(step_id="user", data_schema=self._user_schema())


# ── Options Flow ─────────────────────────────────────────────────


class PaperangOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, _user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if _user_input is not None:
            return self.async_create_entry(data=_user_input)

        current = self._config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TRANSPORT,
                        default=current.get(CONF_TRANSPORT, TRANSPORT_USB),
                    ): vol.In({TRANSPORT_USB: "USB", TRANSPORT_BLE: "Bluetooth BLE"}),
                    vol.Optional(
                        CONF_BLE_ADDRESS,
                        default=current.get(CONF_BLE_ADDRESS, ""),
                    ): str,
                }
            ),
        )
