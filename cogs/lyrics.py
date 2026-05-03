"""Letra de la canción actual o por búsqueda."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

import aiohttp
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("discord.lyrics")

# Limpia sufijos comunes de títulos de YouTube: (Official Video), [HD], (Lyrics), etc.
_CLEAN_RE = re.compile(r"\s*[\(\[][^\)\]]+[\)\]]", re.IGNORECASE)


def _parse_artist_title(query: str) -> tuple[str, str]:
    """Devuelve (artist, title) desde 'Artist - Title'. Si no hay ' - ', artist=''."""
    clean = _CLEAN_RE.sub("", query).strip()
    if " - " in clean:
        artist, title = clean.split(" - ", 1)
        return artist.strip(), title.strip()
    return "", clean


class Lyrics(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def cog_unload(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch(self, artist: str, title: str) -> str | None:
        sess = await self._get_session()
        url = f"https://api.lyrics.ovh/v1/{quote(artist or title)}/{quote(title)}"
        try:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)
                return data.get("lyrics") or None
        except Exception:
            log.warning("Error obteniendo letras: %s - %s", artist, title)
            return None

    @commands.hybrid_command(name="lyrics", description="Letra de la canción actual o búsqueda")
    @app_commands.describe(busqueda="Nombre de la canción (default: la que está sonando)")
    async def lyrics(self, ctx: commands.Context, *, busqueda: str | None = None):
        if ctx.interaction:
            await ctx.defer()

        if busqueda is None:
            music_cog = self.bot.cogs.get("Music")
            player = music_cog.players.get(ctx.guild.id) if music_cog else None
            if not player or not player.current:
                await ctx.send("No hay ninguna canción sonando. Usa `/lyrics <nombre>`.")
                return
            query = player.current.title
        else:
            query = busqueda

        artist, title = _parse_artist_title(query)
        text = await self._fetch(artist, title)

        # Reintento sin artista si la búsqueda inicial falló
        if not text and artist:
            text = await self._fetch("", title)

        if not text:
            await ctx.send(f"No encontré letra para **{query}**.")
            return

        header = f"🎵 **{query}**\n\n"
        full = (header + text.strip()).replace("\r\n", "\n")

        if len(full) <= 2000:
            await ctx.send(full)
            return

        # Enviar en fragmentos respetando saltos de línea (máx 3 mensajes)
        lines = full.splitlines(keepends=True)
        chunk = ""
        sent = 0
        for line in lines:
            if len(chunk) + len(line) > 1900:
                await ctx.send(chunk)
                sent += 1
                chunk = line
                if sent >= 3:
                    await ctx.send("*(letra recortada por ser demasiado larga)*")
                    return
            else:
                chunk += line
        if chunk:
            await ctx.send(chunk)


async def setup(bot: commands.Bot):
    await bot.add_cog(Lyrics(bot))
