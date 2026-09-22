"""Async client for the LaTablée REST API (repo 1, /api/v1).

All endpoints accept device tokens via Bearer auth. Errors raise
LaTableeError with the status code attached.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API = "/api/v1"


class LaTableeError(Exception):
    """Base error; carries the HTTP status when it came from the wire."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class LaTableeConnection:
    """Thin async client for one LaTablée instance."""

    def __init__(
        self,
        base_url: str,
        token: str,
        verify_tls: bool = True,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._token = token
        self._own_session = session is None
        self._session = session
        self._connector = aiohttp.TCPConnector(ssl=verify_tls)

    async def close(self) -> None:
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def _ensure(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(connector=self._connector)
        return self._session

    async def _request(
        self, method: str, path: str, *, json_body: Any = None, params: dict | None = None
    ) -> Any:
        url = f"{self._base}{API}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            sess = await self._ensure()
            async with sess.request(
                method, url, json=json_body, params=params, headers=headers
            ) as resp:
                if resp.status == 204:
                    return None
                text = await resp.text()
                data: Any = None
                if text:
                    try:
                        data = parse_json(text)
                    except ValueError:
                        pass
                if resp.status >= 400:
                    detail = data.get("detail") if isinstance(data, dict) else None
                    raise LaTableeError(detail or f"HTTP {resp.status}", resp.status)
                return data
        except LaTableeError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise LaTableeError(f"Connection failed: {err}") from err

    # ---- health --------------------------------------------------------
    async def health(self) -> dict:
        return await self._request("GET", "/../health")  # /api/health (outside /v1)

    # ---- auth / me -----------------------------------------------------
    async def me(self) -> dict:
        return await self._request("GET", "/auth/me")

    # ---- shopping lists ------------------------------------------------
    async def lists(self) -> list:
        data = await self._request("GET", "/lists")
        return data if isinstance(data, list) else []

    async def list_detail(self, list_id: int) -> dict:
        return await self._request("GET", f"/lists/{list_id}")

    async def add_list_item(
        self, list_id: int, name: str, quantity: float | None = None, unit: str | None = None
    ) -> dict:
        return await self._request(
            "POST", f"/lists/{list_id}/items",
            json_body={"name": name, "quantity": quantity, "unit": unit},
        )

    async def check_item(self, list_id: int, item_id: int, done: bool) -> dict:
        return await self._request(
            "PATCH", f"/lists/{list_id}/items/{item_id}", json_body={"done": done}
        )

    async def remove_item(self, list_id: int, item_id: int) -> None:
        await self._request("DELETE", f"/lists/{list_id}/items/{item_id}")

    # ---- plan ----------------------------------------------------------
    async def plan(self, start: str | None = None, days: int = 7) -> dict:
        params: dict = {"days": days}
        if start:
            params["start"] = start
        return await self._request("GET", "/plan", params=params)

    async def add_plan_entry(self, date: str, slot: str, title: str | None = None,
                             recipe_id: int | None = None) -> dict:
        return await self._request(
            "POST", "/plan",
            json_body={"date": date, "slot": slot,
                       "title_override": title if not recipe_id else None,
                       "recipe_id": recipe_id},
        )

    async def delete_plan_entry(self, entry_id: int) -> None:
        await self._request("DELETE", f"/plan/{entry_id}")

    # ---- recipes -------------------------------------------------------
    async def recipes(self, q: str = "") -> list:
        params = {"q": q} if q else None
        return await self._request("GET", "/recipes", params=params)

    # ---- voice / NLU ---------------------------------------------------
    async def voice_command(self, transcript: str, device_hint: str | None = None) -> dict:
        body: dict = {"transcript": transcript}
        if device_hint:
            body["device_hint"] = device_hint
        return await self._request("POST", "/voice/command", json_body=body)

    # ---- events (polling for sync) --------------------------------------
    async def events(self, after_id: int = 0, limit: int = 100) -> list:
        data = await self._request(
            "GET", "/events", params={"after_id": after_id, "limit": limit}
        )
        return data.get("events", []) if isinstance(data, dict) else []


def parse_json(text: str) -> Any:
    import json

    return json.loads(text)