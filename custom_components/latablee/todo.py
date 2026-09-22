"""Tier 1: shopping list mirrored into a HA todo list entity (two-way)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([LaTableeTodoEntity(coordinator, entry)])


class LaTableeTodoEntity(CoordinatorEntity, TodoListEntity):
    """The active LaTablée shopping list as a HA to-do list."""

    _attr_name = "LaTablée shopping list"
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}-shopping-list"

    @property
    def supported_features(self) -> TodoListEntityFeature:
        return (
            TodoListEntityFeature.CREATE_TODO_ITEM
            | TodoListEntityFeature.UPDATE_TODO_ITEM
            | TodoListEntityFeature.DELETE_TODO_ITEM
        )

    def _list_id(self) -> int | None:
        data = self.coordinator.data or {}
        lst = data.get("list")
        return lst.get("id") if lst else None

    @property
    def todo_items(self) -> list[TodoItem] | None:
        data = self.coordinator.data or {}
        lst = data.get("list")
        if not lst:
            return []
        items = []
        for it in lst.get("items", []):
            # attribution: show which meals need this item
            summary = it.get("name", "")
            attrs = []
            if it.get("quantity") is not None:
                q = it["quantity"]
                q = int(q) if q == int(q) else q
                attrs.append(f"{q} {it['unit'] or ''}".strip())
            froms = it.get("from_recipe_titles") or []
            if froms:
                attrs.append("for " + " · ".join(froms))
            if attrs:
                summary = f"{summary} ({', '.join(attrs)})"
            items.append(
                TodoItem(
                    uid=str(it["id"]),
                    summary=summary,
                    status=TodoItemStatus.COMPLETED if it.get("done") else TodoItemStatus.NEEDS_ACTION,
                )
            )
        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Assist: 'add milk to the shopping list' → POST /lists/N/items."""
        list_id = self._list_id()
        if list_id is None:
            return
        name = item.summary
        quantity = None
        unit = None
        # simple "2 cups milk" / "500 g flour" split
        parts = name.split(" ", 2)
        if len(parts) == 3 and _as_number(parts[0]) is not None:
            quantity = _as_number(parts[0])
            unit = parts[1].lower()
            name = parts[2]
        await self.coordinator.conn.add_list_item(list_id, name, quantity, unit)
        await self.coordinator.async_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        list_id = self._list_id()
        if list_id is None or item.uid is None:
            return
        done = item.status == TodoItemStatus.COMPLETED
        await self.coordinator.conn.check_item(list_id, int(item.uid), done)
        await self.coordinator.async_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        list_id = self._list_id()
        if list_id is None:
            return
        for uid in uids:
            await self.coordinator.conn.remove_item(list_id, int(uid))
        await self.coordinator.async_refresh()


def _as_number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        # "½", "half"
        if text in ("½", "half", "a half"):
            return 0.5
        if text in ("¼", "a quarter"):
            return 0.25
        return None