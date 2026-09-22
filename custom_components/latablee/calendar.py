"""Tier 1: meal plan mirrored into a HA calendar entity."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([LaTableeCalendarEntity(coordinator, entry)])


class LaTableeCalendarEntity(CoordinatorEntity, CalendarEntity):
    """Next 7 days of planned meals as calendar events."""

    _attr_name = "LaTablée meal plan"
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}-meal-plan"

    @property
    def event(self) -> CalendarEvent | None:
        events = self._events()
        return events[0] if events else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [e for e in self._events() if e.start < end_date and e.end > start_date]

    def _events(self) -> list[CalendarEvent]:
        data = self.coordinator.data or {}
        plan = data.get("plan") or {}
        entries = plan.get("entries", [])
        events: list[CalendarEvent] = []
        for e in entries:
            date_str = e.get("date") or e.get("planned_date")
            if not date_str:
                continue
            day = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            title = e.get("title") or e.get("title_override") or "Planned meal"
            slot = e.get("slot", "dinner")
            # all-day-ish events: meal slots at typical hours
            hour = {"breakfast": 7, "lunch": 12, "dinner": 18}.get(slot, 17)
            tz = dt_util.get_default_time_zone()
            start = datetime(day.year, day.month, day.day, hour, 0, tzinfo=tz)
            events.append(
                CalendarEvent(
                    start=start,
                    end=start + timedelta(hours=2),
                    summary=title,
                    description=f"{slot.capitalize()} — planned in LaTablée",
                )
            )
        events.sort(key=lambda ev: ev.start)
        return events