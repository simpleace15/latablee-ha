"""The LaTablée integration: hub entry, discovery pre-fill, entity/platform setup."""
from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
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
