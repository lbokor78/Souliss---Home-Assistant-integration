"""Config flow for Souliss."""

from __future__ import annotations

import ipaddress
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST

from .const import (
    CONF_GATEWAY_PORT,
    CONF_LOCAL_PORT,
    CONF_NODE_INDEX,
    CONF_USER_INDEX,
    DEFAULT_GATEWAY_PORT,
    DEFAULT_LOCAL_PORT,
    DEFAULT_NODE_INDEX,
    DEFAULT_USER_INDEX,
    DOMAIN,
)
from .protocol import async_probe


class SoulissConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Souliss."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Set up Souliss from the UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()

            try:
                resolved = await self.hass.async_add_executor_job(socket.gethostbyname, host)
                ipaddress.ip_address(resolved)
            except (OSError, ValueError):
                errors["base"] = "invalid_host"
            else:
                await self.async_set_unique_id(resolved)
                self._abort_if_unique_id_configured()

                ok = await async_probe(
                    host=host,
                    gateway_port=int(user_input[CONF_GATEWAY_PORT]),
                    user_index=int(user_input[CONF_USER_INDEX]),
                    node_index=int(user_input[CONF_NODE_INDEX]),
                )
                if ok:
                    return self.async_create_entry(
                        title=f"Souliss {resolved}",
                        data={
                            CONF_HOST: host,
                            CONF_GATEWAY_PORT: int(user_input[CONF_GATEWAY_PORT]),
                            CONF_LOCAL_PORT: int(user_input[CONF_LOCAL_PORT]),
                            CONF_USER_INDEX: int(user_input[CONF_USER_INDEX]),
                            CONF_NODE_INDEX: int(user_input[CONF_NODE_INDEX]),
                        },
                    )
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(
                    CONF_GATEWAY_PORT, default=DEFAULT_GATEWAY_PORT
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(
                    CONF_LOCAL_PORT, default=DEFAULT_LOCAL_PORT
                ): vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
                vol.Required(
                    CONF_USER_INDEX, default=DEFAULT_USER_INDEX
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=254)),
                vol.Required(
                    CONF_NODE_INDEX, default=DEFAULT_NODE_INDEX
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=254)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
