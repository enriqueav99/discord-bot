"""Reproducción de música desde URLs (yt-dlp) con cola por servidor."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands, tasks

log = logging.getLogger("discord.music")

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class Track:
    title: str
    url: str
    requested_by: str
    duration: int | None = None


class GuildPlayer:
    def __init__(self, bot: commands.Bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue: deque[Track] = deque()
        self.current: Track | None = None
        self.volume: float = 0.5
        self._next: asyncio.Event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._idle_seconds = 0

    async def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._player_loop())

    def voice(self) -> discord.VoiceClient | None:
        guild = self.bot.get_guild(self.guild_id)
        return guild.voice_client if guild else None

    async def _player_loop(self):
        while True:
            self._next.clear()
            vc = self.voice()
            if not self.queue or not vc or not vc.is_connected():
                return
            track = self.queue.popleft()
            self.current = track
            try:
                source = discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTS)
                source = discord.PCMVolumeTransformer(source, volume=self.volume)
                vc.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self._next.set))
                channel = self.bot.get_channel(self.bot.config.id_canal_bots)
                if channel:
                    await channel.send(
                        f"▶️ Reproduciendo: **{track.title}** (pidió {track.requested_by})"
                    )
                await self._next.wait()
            except Exception:
                log.exception("Error reproduciendo %s", track.title)
            finally:
                self.current = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}
        self.idle_check.start()

    def cog_unload(self):
        self.idle_check.cancel()

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer(self.bot, guild_id)
        return self.players[guild_id]

    async def _extract(self, query: str) -> dict | None:
        loop = asyncio.get_running_loop()

        def _run():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                return ydl.extract_info(query, download=False)

        try:
            return await loop.run_in_executor(None, _run)
        except Exception:
            log.exception("yt_dlp falló para %s", query)
            return None

    @commands.hybrid_command(name="play", description="Reproduce una URL o búsqueda")
    @app_commands.describe(query="URL de YouTube o términos de búsqueda")
    async def play(self, ctx: commands.Context, *, query: str):
        if ctx.author.voice is None:
            await ctx.send("Debes estar en un canal de voz.")
            return

        await ctx.defer() if ctx.interaction else None

        canal = ctx.author.voice.channel
        if ctx.voice_client is None:
            await canal.connect()
        elif ctx.voice_client.channel != canal:
            await ctx.voice_client.move_to(canal)

        info = await self._extract(query)
        if not info:
            await ctx.send("No pude obtener el audio.")
            return

        if "entries" in info:
            info = info["entries"][0]

        track = Track(
            title=info.get("title", "desconocido"),
            url=info["url"],
            requested_by=str(ctx.author),
            duration=info.get("duration"),
        )

        player = self.get_player(ctx.guild.id)
        player.queue.append(track)
        await player.start()

        if player.current and player.current is not track:
            await ctx.send(f"➕ En cola: **{track.title}** (pos {len(player.queue)})")
        else:
            await ctx.send(f"🎵 Cargando: **{track.title}**")

    @commands.hybrid_command(name="queue", description="Muestra la cola")
    async def queue_cmd(self, ctx: commands.Context):
        player = self.players.get(ctx.guild.id)
        if not player or (not player.current and not player.queue):
            await ctx.send("La cola está vacía.")
            return
        embed = discord.Embed(title="🎶 Cola de reproducción", color=0x1DB954)
        if player.current:
            embed.add_field(
                name="Sonando",
                value=f"**{player.current.title}** — {player.current.requested_by}",
                inline=False,
            )
        if player.queue:
            lista = "\n".join(
                f"`{i + 1}.` {t.title} — *{t.requested_by}*"
                for i, t in enumerate(list(player.queue)[:10])
            )
            embed.add_field(name=f"Siguientes ({len(player.queue)})", value=lista, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="skip", description="Salta la canción actual")
    async def skip(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await ctx.send("⏭️ Saltada.")
        else:
            await ctx.send("No estoy reproduciendo nada.")

    @commands.hybrid_command(name="pause", description="Pausa la reproducción")
    async def pause(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸️ Pausada.")
        else:
            await ctx.send("No hay nada reproduciéndose.")

    @commands.hybrid_command(name="resume", description="Reanuda la reproducción")
    async def resume(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ Reanudada.")
        else:
            await ctx.send("No hay nada pausado.")

    @commands.hybrid_command(name="stop", description="Para y limpia la cola")
    async def stop(self, ctx: commands.Context):
        player = self.players.get(ctx.guild.id)
        if player:
            player.queue.clear()
        vc = ctx.guild.voice_client
        if vc:
            vc.stop()
        await ctx.send("⏹️ Detenido y cola vacía.")

    @commands.hybrid_command(name="nowplaying", description="Canción actual")
    async def nowplaying(self, ctx: commands.Context):
        player = self.players.get(ctx.guild.id)
        if not player or not player.current:
            await ctx.send("No hay nada reproduciéndose.")
            return
        t = player.current
        await ctx.send(f"🎧 **{t.title}** — pidió {t.requested_by}")

    @commands.hybrid_command(name="volume", description="Volumen 0-200")
    @app_commands.describe(nivel="Volumen entre 0 y 200")
    async def volume(self, ctx: commands.Context, nivel: int):
        if nivel < 0 or nivel > 200:
            await ctx.send("El volumen debe estar entre 0 y 200.")
            return
        player = self.get_player(ctx.guild.id)
        player.volume = nivel / 100
        vc = ctx.guild.voice_client
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = player.volume
        await ctx.send(f"🔊 Volumen: {nivel}%")

    @tasks.loop(seconds=60)
    async def idle_check(self):
        for guild in list(self.bot.guilds):
            vc = guild.voice_client
            if not vc or not vc.is_connected():
                continue
            humanos = [m for m in vc.channel.members if not m.bot]
            if not humanos:
                player = self.players.get(guild.id)
                if player:
                    player._idle_seconds += 60
                    if player._idle_seconds >= 120:
                        await vc.disconnect(force=False)
                        player.queue.clear()
                        player._idle_seconds = 0
            else:
                player = self.players.get(guild.id)
                if player:
                    player._idle_seconds = 0

    @idle_check.before_loop
    async def before_idle(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
