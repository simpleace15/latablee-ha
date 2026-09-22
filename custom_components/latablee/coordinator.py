"""Coordinator: polls the LaTablée API and hands fresh data to entities."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LaTableeConnection, LaTableeError

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 60


class LaTableeCoordinator(DataUpdateCoordinator):
    """One poll → plan + list; entities consume from the coordinator."""

    def __init__(self, hass: HomeAssistant, conn: LaTableeConnection) -> None:
        super().__init__(hass, _LOGGER, name="LaTablée", update_interval=timedelta(seconds=SCAN_INTERVAL))
        self.conn = conn
        self.last_event_id = 0

    async def _async_update_data(self) -> dict:
        try:
            plan = await self.conn.plan(days=7)
            lists = await self.conn.lists()
            detail = None
            if lists:
                detail = await self.conn.list_detail(lists[0]["id"])
            events = await self.conn.events(self.last_event_id, limit=50)
            if events:
                self.last_event_id = events[-1]["id"]
            return {"plan": plan, "lists": lists, "list": detail, "events": events}
        except LaTableeError as err:
            raise UpdateFailed(str(err)) from err