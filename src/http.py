"""Mixin de sesión HTTP compartida para cogs que usan aiohttp."""

from __future__ import annotations

import aiohttp


class HttpMixin:
    """Proporciona una sesión aiohttp lazy y reutilizable.

    Subclases deben declarar self._session = None en su __init__.
    """

    async def _get_session(self) -> aiohttp.ClientSession:
        session: aiohttp.ClientSession | None = getattr(self, "_session", None)
        if session is None or session.closed:
            self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        return self._session

    async def cog_unload(self) -> None:
        session: aiohttp.ClientSession | None = getattr(self, "_session", None)
        if session and not session.closed:
            await session.close()
