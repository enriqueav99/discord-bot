"""Comandos de voz: join, leave, sonidos pregrabados, foto webcam."""

from __future__ import annotations

import asyncio
import subprocess

import discord
from discord.ext import commands

from src.leer_csv import comprobar_whitelist


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
            await ctx.send("No estoy en un canal de voz, no me molestes o llamo a Tomás.")

    @commands.hybrid_command(name="rr", description="Reproduce el rickroll")
    async def rr(self, ctx: commands.Context):
        if not comprobar_whitelist(ctx.author.name):
            await ctx.send("Lo siento, te jodes, no tienes permiso para usar este comando.")
            return
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc is None:
            await ctx.send("Debo de estar en un canal de voz para usar este comando.")
            return
        try:
            source = discord.FFmpegPCMAudio("sonidos/rickroll.mp3")
            if vc.is_playing():
                vc.stop()
            vc.play(source)
            await ctx.send("🎶 Rickroll iniciado.")
        except Exception as e:
            await ctx.send(f"Error reproduciendo el sonido: {e}")

    @commands.hybrid_command(name="aloe", description="Foto de la cámara aloe")
    async def aloe(self, ctx: commands.Context):
        if not comprobar_whitelist(ctx.author.name):
            await ctx.send("Lo siento, te jodes, no tienes permiso para usar este comando.")
            return
        cam = self.bot.config.cam_device
        if not cam:
            await ctx.send("La cámara no está configurada (DISCORD_BOT_CAM).")
            return

        loop = asyncio.get_running_loop()
        filename = "/tmp/aloe.jpg"

        def _capture() -> str | None:
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "v4l2",
                "-i",
                cam,
                "-frames:v",
                "1",
                filename,
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=30)
                return filename
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                return None

        result = await loop.run_in_executor(None, _capture)
        if not result:
            await ctx.send("Error al tomar la foto.")
            return

        canal = self.bot.get_channel(self.bot.config.id_canal_bots)
        if canal:
            await canal.send(file=discord.File(result))
            if ctx.channel.id != canal.id:
                await ctx.send("Foto enviada al canal de bots.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Voice(bot))
