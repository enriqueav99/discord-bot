"""Comandos generales del bot."""

from __future__ import annotations

import discord
from discord.ext import commands

from src.info import definir_info


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Mide la latencia del bot")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"pong ({round(self.bot.latency * 1000)} ms)")

    @commands.hybrid_command(name="saludar", description="Saludo del bot")
    async def saludar(self, ctx: commands.Context):
        await ctx.send("Hola, que viva la saltisima trinidad, aqui el admin abuse no existe")

    @commands.hybrid_command(name="info", description="Información del bot")
    async def info(self, ctx: commands.Context):
        await ctx.send(embed=definir_info())

    @commands.hybrid_command(name="help_korea", description="Lista de comandos")
    async def help_korea(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Comandos del Bot de Korea",
            color=0x00AAFF,
        )
        categorias = {
            "General": "ping, saludar, info, help_korea",
            "Diversión": "8ball, dado, moneda, choose, meme, rick",
            "Juegos": "adivina, pokeranking, trivia",
            "Voz": "join, leave, rr, aloe",
            "Música": (
                "play, queue, skip, pause, resume, stop, clearqueue, remove, "
                "shuffle, loop, nowplaying, volume"
            ),
            "Utilidad": "userinfo, serverinfo, avatar, poll, recordatorio",
            "Moderación": "clear, kick, ban, timeout, say",
        }
        for nombre, valor in categorias.items():
            embed.add_field(name=nombre, value=valor, inline=False)
        embed.set_footer(
            text=f"Prefix: {self.bot.config.prefix} • también disponibles como /comando"
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
