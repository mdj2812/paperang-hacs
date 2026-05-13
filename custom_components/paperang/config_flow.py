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

    async def async_migrate_entry(self, hass, config_entry):
        """Migrate v1 → v2: add transport key."""
        if config_entry.version == 1:
            data = dict(config_entry.data)
            data.setdefault(CONF_TRANSPORT, TRANSPORT_USB)
            hass.config_entries.async_update_entry(
                config_entry, data=data, version=2
            )
        return True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return PaperangOptionsFlow(config_entry)

    async def async_step_usb(self, discovery_info):  # pylint: disable=unused-argument
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
