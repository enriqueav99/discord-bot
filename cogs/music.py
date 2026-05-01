"""Reproducción de música de YouTube con cola por servidor."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
from collections import deque
from dataclasses import dataclass
from enum import Enum

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands, tasks

log = logging.getLogger("discord.music")

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

MAX_QUEUE = 200
MAX_PLAYLIST = 50


class LoopMode(Enum):
    OFF = "off"
    TRACK = "track"
    QUEUE = "queue"


@dataclass
class Track:
    title: str
    url: str
    requested_by: str
    text_channel_id: int
    webpage_url: str | None = None
    thumbnail: str | None = None
    duration: int | None = None
    uploader: str | None = None


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "?"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _track_embed(track: Track, *, title: str, color: int) -> discord.Embed:
    embed = discord.Embed(title=title, description=f"**{track.title}**", color=color)
    if track.webpage_url:
        embed.url = track.webpage_url
    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    if track.uploader:
        embed.add_field(name="Canal", value=track.uploader, inline=True)
    embed.add_field(name="Duración", value=_format_duration(track.duration), inline=True)
    embed.add_field(name="Pidió", value=track.requested_by, inline=True)
    return embed


class GuildPlayer:
    def __init__(self, bot: commands.Bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue: deque[Track] = deque()
        self.current: Track | None = None
        self.volume: float = 0.5
        self.loop_mode: LoopMode = LoopMode.OFF
        self._next: asyncio.Event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._idle_seconds = 0
        self._lock = asyncio.Lock()

    async def start(self):
        async with self._lock:
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._player_loop())

    def voice(self) -> discord.VoiceClient | None:
        guild = self.bot.get_guild(self.guild_id)
        return guild.voice_client if guild else None

    async def _player_loop(self):
        while True:
            self._next.clear()
            vc = self.voice()
            if not vc or not vc.is_connected():
                return
            if not self.queue and self.loop_mode != LoopMode.TRACK:
                return

            if self.loop_mode == LoopMode.TRACK and self.current:
                track = self.current
            else:
                track = self.queue.popleft()
                self.current = track
                if self.loop_mode == LoopMode.QUEUE:
                    self.queue.append(track)

            try:
                source = discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTS)
                source = discord.PCMVolumeTransformer(source, volume=self.volume)
                vc.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self._next.set))

                channel = self.bot.get_channel(track.text_channel_id)
                if channel:
                    with contextlib.suppress(discord.HTTPException):
                        await channel.send(
                            embed=_track_embed(track, title="▶️ Reproduciendo", color=0x1DB954)
                        )

                await self._next.wait()
            except Exception:
                log.exception("Error reproduciendo %s", track.title)


def _info_to_track(info: dict, requested_by: str, text_channel_id: int) -> Track | None:
    if not info or not info.get("url"):
        return None
    return Track(
        title=info.get("title") or "desconocido",
        url=info["url"],
        requested_by=requested_by,
        text_channel_id=text_channel_id,
        webpage_url=info.get("webpage_url"),
        thumbnail=info.get("thumbnail"),
        duration=info.get("duration"),
        uploader=info.get("uploader") or info.get("channel"),
    )


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
        except yt_dlp.utils.DownloadError as e:
            log.warning("yt_dlp DownloadError: %s", e)
            return None
        except Exception:
            log.exception("yt_dlp falló para %s", query)
            return None

    @commands.hybrid_command(name="play", description="Reproduce una URL/playlist o búsqueda")
    @app_commands.describe(query="URL o términos de búsqueda")
    async def play(self, ctx: commands.Context, *, query: str):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("Debes estar en un canal de voz.")
            return

        if ctx.interaction:
            await ctx.defer()

        canal_voz = ctx.author.voice.channel
        if ctx.voice_client is None:
            try:
                await canal_voz.connect()
            except (TimeoutError, discord.ClientException) as e:
                await ctx.send(f"No pude unirme al canal: {e}")
                return
        elif ctx.voice_client.channel != canal_voz:
            await ctx.voice_client.move_to(canal_voz)

        info = await self._extract(query)
        if not info:
            await ctx.send("No pude obtener el audio. Puede ser privado o restringido.")
            return

        player = self.get_player(ctx.guild.id)

        entries = info.get("entries")
        if entries is not None:
            entries = [e for e in entries if e][:MAX_PLAYLIST]
            if not entries:
                await ctx.send("La playlist está vacía o no se pudo procesar.")
                return
            added = 0
            for entry in entries:
                if len(player.queue) >= MAX_QUEUE:
                    break
                track = _info_to_track(entry, str(ctx.author), ctx.channel.id)
                if track:
                    player.queue.append(track)
                    added += 1
            await ctx.send(
                f"📥 Añadidas **{added}** canciones de la playlist *{info.get('title', '?')}*."
            )
        else:
            track = _info_to_track(info, str(ctx.author), ctx.channel.id)
            if not track:
                await ctx.send("No pude extraer el audio.")
                return
            if len(player.queue) >= MAX_QUEUE:
                await ctx.send(f"La cola está llena (máx {MAX_QUEUE}).")
                return
            player.queue.append(track)
            if player.current:
                await ctx.send(
                    embed=_track_embed(
                        track, title=f"➕ En cola (pos {len(player.queue)})", color=0x3498DB
                    )
                )

        await player.start()

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
                f"`{i + 1}.` {t.title} — *{t.requested_by}* ({_format_duration(t.duration)})"
                for i, t in enumerate(list(player.queue)[:15])
            )
            extra = f"\n…y {len(player.queue) - 15} más." if len(player.queue) > 15 else ""
            embed.add_field(
                name=f"Siguientes ({len(player.queue)})",
                value=lista + extra,
                inline=False,
            )
        embed.set_footer(
            text=f"Loop: {player.loop_mode.value} • Volumen: {int(player.volume * 100)}%"
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="skip", description="Salta la canción actual")
    async def skip(self, ctx: commands.Context):
        vc = ctx.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
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
            player.loop_mode = LoopMode.OFF
        vc = ctx.guild.voice_client
        if vc:
            vc.stop()
        await ctx.send("⏹️ Detenido y cola vacía.")

    @commands.hybrid_command(
        name="clearqueue", description="Vacía la cola sin parar la canción actual"
    )
    async def clear_queue(self, ctx: commands.Context):
        player = self.players.get(ctx.guild.id)
        if not player or not player.queue:
            await ctx.send("La cola ya está vacía.")
            return
        n = len(player.queue)
        player.queue.clear()
        await ctx.send(f"🧹 Cola vaciada ({n} canciones).")

    @commands.hybrid_command(name="remove", description="Elimina una canción de la cola")
    @app_commands.describe(posicion="Posición en la cola (1 = la siguiente)")
    async def remove(self, ctx: commands.Context, posicion: int):
        player = self.players.get(ctx.guild.id)
        if not player or not player.queue:
            await ctx.send("La cola está vacía.")
            return
        if posicion < 1 or posicion > len(player.queue):
            await ctx.send(f"Posición inválida. La cola tiene {len(player.queue)} elementos.")
            return
        as_list = list(player.queue)
        removed = as_list.pop(posicion - 1)
        player.queue = deque(as_list)
        await ctx.send(f"🗑️ Eliminada: **{removed.title}**")

    @commands.hybrid_command(name="shuffle", description="Mezcla la cola aleatoriamente")
    async def shuffle(self, ctx: commands.Context):
        player = self.players.get(ctx.guild.id)
        if not player or len(player.queue) < 2:
            await ctx.send("Necesito al menos 2 canciones en cola para mezclar.")
            return
        as_list = list(player.queue)
        random.shuffle(as_list)
        player.queue = deque(as_list)
        await ctx.send(f"🔀 Cola mezclada ({len(player.queue)} canciones).")

    @commands.hybrid_command(name="loop", description="Modo loop: off, track o queue")
    @app_commands.describe(modo="off, track o queue")
    @app_commands.choices(
        modo=[
            app_commands.Choice(name="off", value="off"),
            app_commands.Choice(name="track", value="track"),
            app_commands.Choice(name="queue", value="queue"),
        ]
    )
    async def loop_cmd(self, ctx: commands.Context, modo: str):
        try:
            mode = LoopMode(modo.lower())
        except ValueError:
            await ctx.send("Modo inválido. Usa `off`, `track` o `queue`.")
            return
        player = self.get_player(ctx.guild.id)
        player.loop_mode = mode
        emoji = {"off": "▶️", "track": "🔂", "queue": "🔁"}[mode.value]
        await ctx.send(f"{emoji} Loop: **{mode.value}**")

    @commands.hybrid_command(name="nowplaying", description="Canción actual con detalles")
    async def nowplaying(self, ctx: commands.Context):
        player = self.players.get(ctx.guild.id)
        if not player or not player.current:
            await ctx.send("No hay nada reproduciéndose.")
            return
        await ctx.send(embed=_track_embed(player.current, title="🎧 Sonando ahora", color=0x1DB954))

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
                        player.loop_mode = LoopMode.OFF
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
