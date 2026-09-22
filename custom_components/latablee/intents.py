# Register custom sentences with the HA intent system.
# custom_sentences/en.yaml is auto-loaded by HA when the integration is installed;
# this module wires the intent handlers themselves.
from __future__ import annotations

from homeassistant.core import HomeAssistant

from .conversation import PlanMealIntentHandler, QueryPlanIntentHandler


async def async_setup_intents(hass: HomeAssistant) -> None:
    from homeassistant.helpers import intent

    intent.async_register(hass, PlanMealIntentHandler())
    intent.async_register(hass, QueryPlanIntentHandler())