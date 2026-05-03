"""Comandos de voz: join, leave, sonidos pregrabados, tts."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from src.whitelist import is_whitelisted

try:
    from gtts import gTTS

    _TTS_OK = True
except ImportError:
    _TTS_OK = False

log = logging.getLogger("discord.voice")

_RICKROLL = Path(__file__).parent.parent / "sonidos" / "rickroll.mp3"


class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="join", description="El bot se une a tu canal de voz")
    async def join(self, ctx: commands.Context):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("Debes estar en un canal de voz para usar este comando.")
            return
        canal = ctx.author.voice.channel
        try:
            if ctx.voice_client is None:
                await canal.connect(reconnect=False)
            else:
                await ctx.voice_client.move_to(canal)
            await ctx.send(f"Me he unido a **{canal}**")
        except discord.errors.ConnectionClosed as e:
            if ctx.guild.voice_client:
                await ctx.guild.voice_client.disconnect(force=True)
            await ctx.send(
                f"No se pudo conectar (error {e.code}). Espera ~30 s e inténtalo de nuevo."
            )
        except Exception as e:
            await ctx.send(f"Error: {e}")

    @commands.hybrid_command(name="leave", description="El bot abandona el canal de voz")
    async def leave(self, ctx: commands.Context):
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc:
            await vc.disconnect(force=False)
            await ctx.send("Adiós.")
        else:
            await ctx.send("No estoy en ningún canal de voz.")

    @commands.hybrid_command(name="rr", description="Reproduce el rickroll")
    async def rr(self, ctx: commands.Context):
        if not is_whitelisted(ctx.author.id):
            await ctx.send("No tienes permiso para usar este comando.")
            return
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc is None:
            await ctx.send("Debo de estar en un canal de voz para usar este comando.")
            return
        try:
            source = discord.FFmpegPCMAudio(str(_RICKROLL))
            if vc.is_playing():
                vc.stop()
            vc.play(source)
            await ctx.send("🎶 Rickroll iniciado.")
        except Exception as e:
            await ctx.send(f"Error reproduciendo el sonido: {e}")

    @commands.hybrid_command(name="tts", description="Reproduce un texto en el canal de voz")
    @app_commands.describe(texto="Texto a reproducir (máx 200 caracteres)")
    async def tts(self, ctx: commands.Context, *, texto: str):
        if not is_whitelisted(ctx.author.id):
            await ctx.send("No tienes permiso para usar este comando.", ephemeral=True)
            return
        if not _TTS_OK:
            await ctx.send("TTS no disponible (instala `gtts`).")
            return
        if len(texto) > 200:
            await ctx.send("Máximo 200 caracteres.")
            return
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc is None:
            await ctx.send("El bot no está en un canal de voz.")
            return

        loop = asyncio.get_running_loop()
        path = f"/tmp/tts_{ctx.guild.id}.mp3"

        def _generate():
            gTTS(text=texto, lang="es").save(path)

        try:
            await loop.run_in_executor(None, _generate)
        except Exception as e:
            await ctx.send(f"Error generando TTS: {e}")
            return

        if vc.is_playing():
            vc.stop()

        def _cleanup(_err: Exception | None) -> None:
            with contextlib.suppress(OSError):
                os.unlink(path)

        vc.play(discord.FFmpegPCMAudio(path), after=_cleanup)
        preview = texto[:60] + ("…" if len(texto) > 60 else "")
        await ctx.send(f"🔊 *{preview}*")


async def setup(bot: commands.Bot):
    await bot.add_cog(Voice(bot))
