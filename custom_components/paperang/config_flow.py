# pylint: disable=import-error
"""Config flow for Paperang P2 Printer integration.

USB discovery scans for all compatible devices and lets the user
pick one.  Each device is identified by its USB bus + port path so
multiple printers can coexist.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    TRANSPORT_USB,
    TRANSPORT_BLE,
    CONF_TRANSPORT,
    CONF_BLE_ADDRESS,
    CONF_USB_BUS,
    CONF_USB_PORT,
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

    devices = usb.core.find(find_all=True, idVendor=PAPERANG_VID,
                            idProduct=PAPERANG_PID)
    result: list[dict[str, Any]] = []
    for dev in devices:
        port = list(dev.port_numbers) if dev.port_numbers else []
        usb_path = "-".join(str(p) for p in [dev.bus] + port)
        result.append({
            "usb_path": usb_path,
            "bus": dev.bus,
            "port": port,
            "address": dev.address,
        })
    return result


def _verify_printer(bus: int, port: list[int]) -> bool:
    """Quick check: connect to the device and read battery.

    Returns True on success, False on any error.
    """
    try:
        # Import inside so the config flow doesn't require the full lib
        import paperang  # pylint: disable=import-outside-toplevel,import-self
    except ImportError:
        return False

    from . import UsbTransportWithPath  # pylint: disable=import-outside-toplevel

    printer = paperang.PaperangP2(
        transport=UsbTransportWithPath(bus=bus, port=port)
    )
    try:
        printer.connect()
        battery = printer.get_battery()
        return battery is not None
    except Exception:
        return False
    finally:
        try:
            printer.disconnect()
        except Exception:
            pass


# ── Config Flow ──────────────────────────────────────────────────


class PaperangConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Paperang P2 Printer."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise."""
        super().__init__()
        self._discovered: list[dict[str, Any]] = []
        self._selected_device: dict[str, Any] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return PaperangOptionsFlow(config_entry)

    # ── USB discovery ─────────────────────────────────────────

    async def async_step_usb(self, discovery_info=None):
        """Handle USB discovery — scan for Paperang devices."""
        # pylint: disable=unused-argument
        self._discovered = await self.hass.async_add_executor_job(
            _scan_usb_devices
        )

        if not self._discovered:
            return self.async_abort(reason="no_usb_device_found")

        # Single device → skip selection, go straight to verify
        if len(self._discovered) == 1:
            self._selected_device = self._discovered[0]
            return await self.async_step_verify()

        return await self.async_step_select_device()

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ):
        """Let the user pick which USB device to use."""
        errors: dict[str, str] = {}

        if user_input is not None:
            chosen_path = user_input["usb_device"]
            for dev in self._discovered:
                if dev["usb_path"] == chosen_path:
                    self._selected_device = dev
                    break

            if self._selected_device is None:
                errors["usb_device"] = "device_not_found"
            else:
                return await self.async_step_verify()

        # Build dropdown options
        options = {
            dev["usb_path"]: (
                f"Paperang P2 — USB {dev['usb_path']}"
                f" (bus {dev['bus']}, addr {dev['address']})"
            )
            for dev in self._discovered
        }

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("usb_device"): vol.In(options),
            }),
            errors=errors,
        )

    async def async_step_verify(
        self, user_input: dict[str, Any] | None = None  # pylint: disable=unused-argument
    ):
        """Verify communication with the selected device."""
        if self._selected_device is None:
            return self.async_abort(reason="no_usb_device_found")

        dev = self._selected_device
        usb_path = dev["usb_path"]

        # Set unique_id based on USB path so HA can tell devices apart
        await self.async_set_unique_id(f"paperang_usb_{usb_path}")
        self._abort_if_unique_id_configured()

        ok = await self.hass.async_add_executor_job(
            _verify_printer, dev["bus"], dev["port"]
        )

        if not ok:
            return self.async_show_form(
                step_id="verify",
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

    # ── Manual / import / BLE ──────────────────────────────────

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle the initial step (manual add)."""
        transport = (
            user_input.get(CONF_TRANSPORT, TRANSPORT_USB)
            if user_input
            else TRANSPORT_USB
        )

        if user_input is not None:
            if transport == TRANSPORT_USB:
                # USB manual add — scan for devices
                self._discovered = await self.hass.async_add_executor_job(
                    _scan_usb_devices
                )
                if not self._discovered:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema({
                            vol.Required(CONF_TRANSPORT, default=TRANSPORT_USB): vol.In({
                                TRANSPORT_USB: "USB",
                                TRANSPORT_BLE: "Bluetooth BLE",
                            }),
                            vol.Optional(CONF_BLE_ADDRESS): str,
                        }),
                        errors={"base": "no_usb_device_found"},
                    )
                if len(self._discovered) == 1:
                    self._selected_device = self._discovered[0]
                    return await self.async_step_verify()
                return await self.async_step_select_device()

            # BLE path
            ble_addr = user_input.get(CONF_BLE_ADDRESS, "")
            unique_id = f"paperang_ble_{ble_addr}" if ble_addr else "paperang_ble"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Paperang P2 Printer (BLE)",
                data={
                    CONF_TRANSPORT: TRANSPORT_BLE,
                    CONF_BLE_ADDRESS: ble_addr,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_TRANSPORT, default=TRANSPORT_USB): vol.In({
                    TRANSPORT_USB: "USB",
                    TRANSPORT_BLE: "Bluetooth BLE",
                }),
                vol.Optional(CONF_BLE_ADDRESS): str,
            }),
        )


# ── Options Flow ─────────────────────────────────────────────────


class PaperangOptionsFlow(config_entries.OptionsFlow):  # pylint: disable=too-few-public-methods
    """Handle options flow."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None  # pylint: disable=unused-argument
    ):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self._config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_TRANSPORT,
                    default=current.get(CONF_TRANSPORT, TRANSPORT_USB),
                ): vol.In({
                    TRANSPORT_USB: "USB",
                    TRANSPORT_BLE: "Bluetooth BLE",
                }),
                vol.Optional(
                    CONF_BLE_ADDRESS,
                    default=current.get(CONF_BLE_ADDRESS, ""),
                ): str,
            }),
        )
