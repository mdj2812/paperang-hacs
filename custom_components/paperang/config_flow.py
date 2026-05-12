"""Config flow for Paperang P2 Printer integration."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class PaperangConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # pylint: disable=too-few-public-methods
    """Handle a config flow for Paperang P2 Printer."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return PaperangOptionsFlow(config_entry)

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle the initial step (auto-detect or confirm)."""
        if user_input is not None:
            return self.async_create_entry(
                title="Paperang P2 Printer",
                data={},
            )

        return self.async_show_form(step_id="user")


class PaperangOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage the options."""
        return self.async_show_form(step_id="init")
