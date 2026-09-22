"""The LaTablée integration: hub entry, discovery pre-fill, entity/platform setup."""
from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LaTableeConnection, LaTableeError
from .const import CONF_TOKEN, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up via YAML is not supported — config flow only."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    url: str = entry.data[CONF_URL]
    token: str = entry.data[CONF_TOKEN]
    verify: bool = entry.data.get(CONF_VERIFY_SSL, True)

    conn = LaTableeConnection(url, token, verify, async_get_clientsession(hass))
    try:
        me = await conn.me()
    except LaTableeError as err:
        _LOGGER.warning("LaTablée unreachable at setup: %s", err)
        raise
    if me.get("household_id") is None:
        raise vol.Invalid("That user has no household — finish LaTablée onboarding first.")

    from .coordinator import LaTableeCoordinator

    coordinator = LaTableeCoordinator(hass, conn)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"conn": conn, "me": me, "coordinator": coordinator}

    # Tier 2: register intent handlers (idempotent — registered once per handler class)
    from .intents import async_setup_intents

    await async_setup_intents(hass)

    # Services for scripts/automations
    from .services import async_setup_services

    await async_setup_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Tier 2/3: register intents + services once
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload:
        conn: LaTableeConnection = hass.data[DOMAIN].pop(entry.entry_id)["conn"]
        await conn.close()
    return unload


# --------------------------------------------------------------------------
# Config flow (URL + token; discovery pre-fills both when add-on installed)
# --------------------------------------------------------------------------
class LaTableeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the LaTablée config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        suggested = {"url": "", "token": ""}

        # Supervisor discovery: the add-on stores instance_url/api_token in its
        # options; when the same Supervisor runs, pre-fill from its discovery info.
        discovery = await self._async_discovery()
        if discovery:
            suggested = discovery

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
        await self._async_handle_discovery(discovery_info)
        return await self.async_step_user()

    async def _async_discovery(self) -> dict | None:
        """Read discovery info pushed by the add-on (hassio discovery payload)."""
        return getattr(self, "_discovery_info", None)

    async def _async_handle_discovery(self, discovery_info: dict[str, Any]) -> None:
        self._discovery_info = {
            "url": discovery_info.get("url", ""),
            "token": discovery_info.get("token", ""),
        }