# pylint: disable=import-error
"""Config flow for Paperang P2 Printer integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, TRANSPORT_USB, TRANSPORT_BLE, CONF_TRANSPORT, CONF_BLE_ADDRESS


class PaperangConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # pylint: disable=too-few-public-methods
    """Handle a config flow for Paperang P2 Printer."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return PaperangOptionsFlow(config_entry)

    async def async_step_usb(self, _discovery_info):
        """Handle USB discovery."""
        await self.async_set_unique_id("paperang_p2_usb")
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Confirm USB discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title="Paperang P2 Printer",
                data={CONF_TRANSPORT: TRANSPORT_USB},
            )

        return self.async_show_form(step_id="confirm")

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle the initial step (manual add)."""
        if user_input is None:
            # Check for existing entries before showing the form.
            # If both USB and BLE are already configured, abort early.
            usb_exists = any(
                e.unique_id == "paperang_p2_usb"
                for e in self._async_current_entries()
            )
            ble_exists = any(
                e.unique_id == "paperang_p2_ble"
                for e in self._async_current_entries()
            )
            if usb_exists and ble_exists:
                return self.async_abort(reason="already_configured")

        transport = user_input.get(CONF_TRANSPORT, TRANSPORT_USB) if user_input else TRANSPORT_USB
        unique_id = f"paperang_p2_{transport}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            data: dict[str, Any] = {CONF_TRANSPORT: transport}
            if transport == TRANSPORT_BLE:
                data[CONF_BLE_ADDRESS] = user_input.get(CONF_BLE_ADDRESS, "")
            return self.async_create_entry(
                title="Paperang P2 Printer" + (" (BLE)" if transport == TRANSPORT_BLE else ""),
                data=data,
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


class PaperangOptionsFlow(config_entries.OptionsFlow):  # pylint: disable=too-few-public-methods
    """Handle options flow."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, _user_input: dict[str, Any] | None = None
    ):
        """Manage the options."""
        if _user_input is not None:
            return self.async_create_entry(data=_user_input)

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
