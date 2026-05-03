"""Eventos del servidor: bienvenidas, despedidas, error handler global."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

log = logging.getLogger("discord.events")


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        canal = self.bot.get_channel(self.bot.config.id_canal_principal)
        if canal:
            await canal.send(f"👋 {member.mention} se ha unido al servidor.")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        canal = self.bot.get_channel(self.bot.config.id_canal_principal)
        if canal:
            await canal.send(f"**{member}** ha abandonado el servidor.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Falta el argumento `{error.param.name}`.")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Argumento inválido: {error}")
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("No tienes permisos para usar este comando.")
            return
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Espera {error.retry_after:.1f}s.")
            return
        log.exception("Error en comando %s", ctx.command, exc_info=error)
        await ctx.send("Ocurrió un error inesperado.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
