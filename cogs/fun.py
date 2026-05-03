"""Comandos de diversión."""

from __future__ import annotations

import random
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from src.http import HttpMixin

_8BALL_RESPONSES = [
    "Sí, sin duda.",
    "Probablemente.",
    "Lo veo claro.",
    "No cuentes con ello.",
    "Mis fuentes dicen que no.",
    "Pregunta de nuevo más tarde.",
    "Mejor no te lo digo ahora.",
    "Definitivamente no.",
    "Es decididamente así.",
    "Puedes confiar en ello.",
    "Las perspectivas no son tan buenas.",
    "Concéntrate y vuelve a preguntar.",
]

_RIC_IMG = Path(__file__).parent.parent / "img" / "ric.jpg"


class Fun(HttpMixin, commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None

    @commands.hybrid_command(name="8ball", description="Pregunta a la bola mágica")
    @app_commands.describe(pregunta="Lo que quieras preguntar")
    async def eight_ball(self, ctx: commands.Context, *, pregunta: str):
        await ctx.send(f"🎱 **{pregunta}**\n> {random.choice(_8BALL_RESPONSES)}")

    @commands.hybrid_command(name="dado", description="Tira un dado de N caras")
    @app_commands.describe(caras="Número de caras (default 6)")
    async def dado(self, ctx: commands.Context, caras: int = 6):
        if caras < 2 or caras > 1000:
            await ctx.send("El dado debe tener entre 2 y 1000 caras.")
            return
        await ctx.send(f"🎲 d{caras}: **{random.randint(1, caras)}**")

    @commands.hybrid_command(name="moneda", description="Cara o cruz")
    async def moneda(self, ctx: commands.Context):
        await ctx.send(f"🪙 {random.choice(['Cara', 'Cruz'])}")

    @commands.hybrid_command(name="choose", description="Elige una opción aleatoria")
    @app_commands.describe(opciones="Opciones separadas por |")
    async def choose(self, ctx: commands.Context, *, opciones: str):
        partes = [p.strip() for p in opciones.split("|") if p.strip()]
        if len(partes) < 2:
            await ctx.send("Pásame al menos 2 opciones separadas por `|`.")
            return
        await ctx.send(f"🤔 Elijo: **{random.choice(partes)}**")

    @commands.hybrid_command(name="meme", description="Un meme aleatorio de Reddit")
    async def meme(self, ctx: commands.Context):
        await ctx.defer() if ctx.interaction else None
        try:
            session = await self._get_session()
            async with session.get(
                "https://meme-api.com/gimme", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    await ctx.send("No pude obtener un meme ahora mismo.")
                    return
                data = await resp.json()
        except (TimeoutError, aiohttp.ClientError):
            await ctx.send("Timeout obteniendo el meme.")
            return

        embed = discord.Embed(title=data.get("title", "meme"), color=0xFF5500)
        embed.set_image(url=data["url"])
        embed.set_footer(text=f"r/{data.get('subreddit', '?')} • 👍 {data.get('ups', 0)}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rick", description="Manda al rick")
    async def rick(self, ctx: commands.Context):
        canal = self.bot.get_channel(self.bot.config.id_canal_bots)
        if canal is None:
            await ctx.send("No encuentro el canal de bots.")
            return
        try:
            with _RIC_IMG.open("rb") as f:
                await canal.send(file=discord.File(f))
            if ctx.channel.id != canal.id:
                await ctx.send("Enviado al canal de bots.", ephemeral=True)
        except FileNotFoundError:
            await ctx.send("No se pudo encontrar la imagen.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
