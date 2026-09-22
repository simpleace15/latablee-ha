"""Tier 2: custom intents (fast local match) + Tier 3: conversation agent (app NLU)."""
from __future__ import annotations

import logging
import re

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([LaTableeAgent(hass, entry)])


# ---- Tier 2: intent handlers -------------------------------------------------

DATE_WORDS = {
    "tonight": 0, "today": 0,
    "tomorrow": 1,
    "monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH",
    "friday": "FR", "saturday": "SA", "sunday": "SU",
}


class PlanMealIntentHandler(intent.IntentHandler):
    """'add tacos for dinner Wednesday' / 'plan lasagna tomorrow night'."""

    intent_type = "latablee_plan_meal"
    description = "Plan a meal into LaTablée"
    slot_schema = {"meal": str, "day": str, "slot": str}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass = intent_obj.hass
        slots = {k: v["value"] for k, v in (intent_obj.slots or {}).items() if v.get("value")}
        meal = slots.get("meal", "")
        day = slots.get("day", "tonight")
        slot = slots.get("slot", "dinner")
        if not meal:
            response = intent_obj.create_response()
            response.async_set_speech("What meal should I plan?")
            return response
        conn, _ = _get_conn(hass)
        date = _resolve_date(day)
        entry_rec = await conn.add_plan_entry(date, slot.lower(), title=meal)
        response = intent_obj.create_response()
        response.async_set_speech(f"{meal} is on the menu for {day}.")
        return response


class QueryPlanIntentHandler(intent.IntentHandler):
    """'what's for dinner tonight'."""

    intent_type = "latablee_query_plan"
    description = "Ask LaTablée what is planned"
    slot_schema = {"day": str, "slot": str}

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass = intent_obj.hass
        slots = {k: v["value"] for k, v in (intent_obj.slots or {}).items() if v.get("value")}
        day = slots.get("day", "tonight")
        slot = slots.get("slot", "dinner")
        conn, _ = _get_conn(hass)
        plan = await conn.plan(days=8)
        date = _resolve_date(day)
        for e in plan.get("entries", []):
            e_date = (e.get("date") or e.get("planned_date") or "")[:10]
            if e_date == date and e.get("slot", "dinner").lower() == slot.lower():
                title = e.get("title") or e.get("title_override") or "nothing planned"
                response = intent_obj.create_response()
                response.async_set_speech(f"{slot} on {day} is {title}.")
                return response
        response = intent_obj.create_response()
        response.async_set_speech(f"{slot} on {day} is open — want me to plan something?")
        return response


# ---- Tier 3: freeform conversation agent --------------------------------------

class LaTableeAgent(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    """'Ask LaTablée …' — forwards freeform requests to the app's /voice/command NLU."""

    _attr_name = "Ask LaTablée"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}-conversation"

    @property
    def supported_languages(self) -> list[str]:
        return ["*"]  # language-agnostic; the app's NLU handles what it can

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        conn, _ = _get_conn(self.hass)
        device_hint = _extract_hint(user_input.text)
        try:
            result = await conn.voice_command(user_input.text, device_hint)
            reply = result.get("reply") or "Done."
        except Exception as err:  # noqa: BLE001 — report, don't crash the pipeline
            _LOGGER.warning("LaTablée voice command failed: %s", err)
            reply = f"LaTablée couldn't handle that: {err}"
        response = conversation.async_create_result(
            agent_id=self.entity_id, conversation=user_input.conversation_id or None
        )
        # note: use intent helper for a plain speech reply
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(reply)
        return conversation.ConversationResult(
            response=intent_response, conversation_id=user_input.conversation_id
        )


# ---- shared helpers ------------------------------------------------------------

def _get_conn(hass: HomeAssistant):
    for store in hass.data.get(DOMAIN, {}).values():
        return store["conn"], store
    raise RuntimeError("LaTablée integration not configured")


def _resolve_date(day: str) -> str:
    from datetime import date as d, timedelta

    day = (day or "tonight").lower().strip()
    today = d.today()
    if day in ("tonight", "today"):
        return today.isoformat()
    if day == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if day in DATE_WORDS and isinstance(DATE_WORDS[day], str):
        target = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(day)
        delta = (target - today.weekday()) % 7 or 7
        return (today + timedelta(days=delta)).isoformat()
    # ISO passthrough
    if re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        return day
    return today.isoformat()


def _extract_hint(text: str) -> str | None:
    """If the transcript mentions a wake-word-ish name, pass it for fuzzy matching."""
    lowered = text.lower()
    for hint in ("latablee", "la table", "latable", "the table"):
        if hint in lowered:
            return hint
    return None