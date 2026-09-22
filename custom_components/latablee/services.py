"""Services: kitchen/automations surface — add_to_list, plan_meal, query_plan, voice_command."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .conversation import _get_conn, _resolve_date

_LOGGER = logging.getLogger(__name__)

ATTR_ITEM = "item"
ATTR_QUANTITY = "quantity"
ATTR_UNIT = "unit"
ATTR_MEAL = "meal"
ATTR_DATE = "date"
ATTR_SLOT = "slot"
ATTR_DAYS = "days"
ATTR_TRANSCRIPT = "transcript"


async def async_setup_services(hass: HomeAssistant) -> None:
    from .const import DOMAIN as _D  # noqa: F401

    if hass.services.has_service(DOMAIN, "add_to_list"):
        return  # already registered

    async def add_to_list(call: ServiceCall) -> None:
        conn, _ = _get_conn(hass)
        lists = await conn.lists()
        if not lists:
            _LOGGER.warning("LaTablée: no shopping list exists yet")
            return
        await conn.add_list_item(
            lists[0]["id"], call.data[ATTR_ITEM],
            call.data.get(ATTR_QUANTITY), call.data.get(ATTR_UNIT),
        )

    async def plan_meal(call: ServiceCall) -> None:
        conn, _ = _get_conn(hass)
        await conn.add_plan_entry(
            call.data[ATTR_DATE], call.data.get(ATTR_SLOT, "dinner"),
            title=call.data[ATTR_MEAL],
        )

    async def query_plan(call: ServiceCall) -> None:
        conn, _ = _get_conn(hass)
        plan = await conn.plan(days=call.data.get(ATTR_DAYS, 7))
        hass.bus.async_fire(
            f"{DOMAIN}_plan_query_result", {"entries": plan.get("entries", [])}
        )

    async def voice_command(call: ServiceCall) -> None:
        conn, _ = _get_conn(hass)
        result = await conn.voice_command(call.data[ATTR_TRANSCRIPT])
        hass.bus.async_fire(f"{DOMAIN}_voice_result", result)

    hass.services.async_register(DOMAIN, "add_to_list", add_to_list)
    hass.services.async_register(DOMAIN, "plan_meal", plan_meal)
    hass.services.async_register(DOMAIN, "query_plan", query_plan)
    hass.services.async_register(DOMAIN, "voice_command", voice_command)