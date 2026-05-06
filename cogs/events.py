"""Eventos del servidor: bienvenidas, despedidas, logging extendido, error handler."""

from __future__ import annotations

import contextlib
import logging

import discord
from discord.ext import commands

log = logging.getLogger("discord.events")


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _log_canal(self) -> discord.TextChannel | None:
        canal_id = self.bot.config.id_canal_logs
        return self.bot.get_channel(canal_id) if canal_id else None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        role = discord.utils.get(member.guild.roles, name="salmanternis")
        if role:
            try:
                await member.add_roles(role, reason="Rol automático al unirse")
            except discord.Forbidden:
                log.warning("Sin permisos para asignar el rol 'salmanternis' a %s", member)
            except discord.HTTPException as e:
                log.warning("Error asignando rol a %s: %s", member, e)

        canal = self.bot.get_channel(self.bot.config.id_canal_principal)
        if canal:
            await canal.send(f"{member.mention} entró al servidor, ya me jodería.")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        canal = self.bot.get_channel(self.bot.config.id_canal_principal)
        if canal:
            await canal.send(f"**{member}** ha abandonado el servidor.")

    # ── logging extendido ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        log_ch = self._log_canal()
        if not log_ch:
            return
        embed = discord.Embed(title="✏️ Mensaje editado", color=0x3498DB, url=after.jump_url)
        embed.add_field(
            name="Usuario", value=f"{before.author.mention} (`{before.author}`)", inline=True
        )
        embed.add_field(name="Canal", value=before.channel.mention, inline=True)
        embed.add_field(name="Antes", value=before.content[:500] or "*(vacío)*", inline=False)
        embed.add_field(name="Después", value=after.content[:500] or "*(vacío)*", inline=False)
        embed.timestamp = discord.utils.utcnow()
        with contextlib.suppress(discord.HTTPException):
            await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        log_ch = self._log_canal()
        if not log_ch:
            return
        embed = discord.Embed(title="🗑️ Mensaje eliminado", color=0xE74C3C)
        embed.add_field(
            name="Usuario", value=f"{message.author.mention} (`{message.author}`)", inline=True
        )
        embed.add_field(name="Canal", value=message.channel.mention, inline=True)
        if message.content:
            embed.add_field(name="Contenido", value=message.content[:500], inline=False)
        embed.timestamp = discord.utils.utcnow()
        with contextlib.suppress(discord.HTTPException):
            await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        log_ch = self._log_canal()
        if not log_ch:
            return
        if before.nick != after.nick:
            embed = discord.Embed(title="✏️ Cambio de nick", color=0x9B59B6)
            embed.add_field(name="Usuario", value=f"{after.mention} (`{after}`)", inline=False)
            embed.add_field(name="Antes", value=before.nick or before.name, inline=True)
            embed.add_field(name="Después", value=after.nick or after.name, inline=True)
            embed.timestamp = discord.utils.utcnow()
            with contextlib.suppress(discord.HTTPException):
                await log_ch.send(embed=embed)
        added = [r for r in after.roles if r not in before.roles and not r.is_default()]
        removed = [r for r in before.roles if r not in after.roles and not r.is_default()]
        if added or removed:
            embed = discord.Embed(title="🎭 Cambio de roles", color=0x1ABC9C)
            embed.add_field(name="Usuario", value=f"{after.mention} (`{after}`)", inline=False)
            if added:
                embed.add_field(
                    name="Añadidos", value=" ".join(r.mention for r in added), inline=True
                )
            if removed:
                embed.add_field(
                    name="Eliminados", value=" ".join(r.mention for r in removed), inline=True
                )
            embed.timestamp = discord.utils.utcnow()
            with contextlib.suppress(discord.HTTPException):
                await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        log_ch = self._log_canal()
        if not log_ch:
            return
        embed = discord.Embed(title="➕ Canal creado", color=0x2ECC71)
        embed.add_field(name="Canal", value=f"{channel.mention} (`{channel.name}`)", inline=True)
        embed.add_field(name="Tipo", value=str(channel.type).replace("_", " ").title(), inline=True)
        if hasattr(channel, "category") and channel.category:
            embed.add_field(name="Categoría", value=channel.category.name, inline=True)
        embed.timestamp = discord.utils.utcnow()
        with contextlib.suppress(discord.HTTPException):
            await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        log_ch = self._log_canal()
        if not log_ch:
            return
        embed = discord.Embed(title="➖ Canal eliminado", color=0xE74C3C)
        embed.add_field(name="Canal", value=f"`{channel.name}`", inline=True)
        embed.add_field(name="Tipo", value=str(channel.type).replace("_", " ").title(), inline=True)
        if hasattr(channel, "category") and channel.category:
            embed.add_field(name="Categoría", value=channel.category.name, inline=True)
        embed.timestamp = discord.utils.utcnow()
        with contextlib.suppress(discord.HTTPException):
            await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        log_ch = self._log_canal()
        if not log_ch:
            return
        embed = discord.Embed(title="🔗 Invitación creada", color=0x3498DB)
        embed.add_field(name="Código", value=f"`{invite.code}`", inline=True)
        embed.add_field(
            name="Creador",
            value=invite.inviter.mention if invite.inviter else "desconocido",
            inline=True,
        )
        embed.add_field(
            name="Usos máx.", value=str(invite.max_uses) if invite.max_uses else "∞", inline=True
        )
        embed.add_field(
            name="Expira",
            value=str(invite.expires_at)[:10] if invite.expires_at else "nunca",
            inline=True,
        )
        embed.timestamp = discord.utils.utcnow()
        with contextlib.suppress(discord.HTTPException):
            await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        log_ch = self._log_canal()
        if not log_ch:
            return
        embed = discord.Embed(title="🔗 Invitación eliminada", color=0xE74C3C)
        embed.add_field(name="Código", value=f"`{invite.code}`", inline=True)
        embed.timestamp = discord.utils.utcnow()
        with contextlib.suppress(discord.HTTPException):
            await log_ch.send(embed=embed)

    # ── error handler ────────────────────────────────────────────────────────

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
        if isinstance(error, commands.CheckFailure):
            await ctx.send("No tienes el rol necesario para usar este comando.", ephemeral=True)
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
