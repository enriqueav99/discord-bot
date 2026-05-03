"""Gestión de la whitelist mediante comandos de Discord."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import src.whitelist as wl


class WhitelistCog(commands.Cog, name="Whitelist"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="whitelist", description="Gestión de la whitelist")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def whitelist_group(self, ctx: commands.Context):
        pass

    @whitelist_group.command(name="add", description="Añade un usuario a la whitelist")
    @app_commands.describe(miembro="Usuario a añadir")
    async def add(self, ctx: commands.Context, miembro: discord.Member):
        if wl.add_user(miembro.id):
            await ctx.send(f"✅ **{miembro}** añadido a la whitelist.")
        else:
            await ctx.send(f"⚠️ **{miembro}** ya estaba en la whitelist.")

    @whitelist_group.command(name="remove", description="Elimina un usuario de la whitelist")
    @app_commands.describe(miembro="Usuario a eliminar")
    async def remove(self, ctx: commands.Context, miembro: discord.Member):
        if wl.remove_user(miembro.id):
            await ctx.send(f"🗑️ **{miembro}** eliminado de la whitelist.")
        else:
            await ctx.send(f"⚠️ **{miembro}** no estaba en la whitelist.")

    @whitelist_group.command(name="list", description="Muestra los usuarios en la whitelist")
    async def list_cmd(self, ctx: commands.Context):
        users = wl.list_users()
        if not users:
            await ctx.send("La whitelist está vacía.")
            return

        lineas = []
        for uid in users:
            member = ctx.guild.get_member(uid) if ctx.guild else None
            name = member.mention if member else f"<@{uid}>"
            lineas.append(f"• {name} (`{uid}`)")

        embed = discord.Embed(
            title="📋 Whitelist",
            description="\n".join(lineas),
            color=0x00AAFF,
        )
        await ctx.send(embed=embed)

    @add.error
    @remove.error
    @list_cmd.error
    @whitelist_group.error
    async def perm_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("No tienes permisos para usar este comando.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WhitelistCog(bot))
