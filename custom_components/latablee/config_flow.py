"""Config flow: URL + device token, pre-filled via Supervisor discovery."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_URL, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LaTableeConnection, LaTableeError
from .const import CONF_TOKEN, DOMAIN


class LaTableeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the LaTablée config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        suggested: dict[str, str] = getattr(self, "_discovery_suggest", {}) or {}

        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            token = user_input[CONF_TOKEN]
            verify = user_input.get(CONF_VERIFY_SSL, True)
            conn = LaTableeConnection(url, token, verify, async_get_clientsession(self.hass))
            try:
                me = await conn.me()
            except LaTableeError as err:
                errors["base"] = "cannot_connect" if err.status is None else "invalid_auth"
            else:
                await conn.close()
                await self.async_set_unique_id(f"latablee:{url}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"LaTablée ({me.get('name', 'user')})",
                    data={CONF_URL: url, CONF_TOKEN: token, CONF_VERIFY_SSL: verify},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_URL, default=suggested.get("url", "")): str,
                vol.Required(CONF_TOKEN, default=suggested.get("token", "")): str,
                vol.Required(CONF_VERIFY_SSL, default=True): bool,
            }),
            errors=errors,
        )

    async def async_step_discovery(self, discovery_info: dict[str, Any]):
        """Pre-fill from the add-on's options via Supervisor discovery."""
        self._discovery_suggest = {
            "url": discovery_info.get("url", ""),
            "token": discovery_info.get("token", ""),
        }
        return await self.async_step_user()
