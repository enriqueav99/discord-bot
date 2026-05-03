"""Comandos de moderación."""

from __future__ import annotations

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility import parse_duration


def _log_embed(
    *,
    action: str,
    color: int,
    mod: discord.Member,
    target: discord.Member | None = None,
    reason: str | None = None,
    extra: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(title=f"🔨 {action}", color=color)
    embed.add_field(name="Moderador", value=mod.mention, inline=True)
    if target:
        embed.add_field(name="Usuario", value=f"{target.mention} (`{target}`)", inline=True)
    if reason:
        embed.add_field(name="Razón", value=reason, inline=False)
    if extra:
        embed.add_field(name="Detalle", value=extra, inline=False)
    embed.timestamp = discord.utils.utcnow()
    return embed


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _log_canal(self) -> discord.TextChannel | None:
        canal_id = self.bot.config.id_canal_logs
        return self.bot.get_channel(canal_id) if canal_id else None

    @commands.hybrid_command(name="clear", description="Borra N mensajes recientes")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(cantidad="Número de mensajes a borrar (1-100)")
    async def clear(self, ctx: commands.Context, cantidad: int):
        if cantidad < 1 or cantidad > 100:
            await ctx.send("Entre 1 y 100.", ephemeral=True)
            return
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
            deleted = await ctx.channel.purge(limit=cantidad)
            await ctx.send(f"🧹 Borrados {len(deleted)} mensajes.", ephemeral=True)
        else:
            deleted = await ctx.channel.purge(limit=cantidad + 1)
            confirm = await ctx.send(f"🧹 Borrados {len(deleted) - 1} mensajes.")
            await confirm.delete(delay=3)
        log_ch = self._log_canal()
        if log_ch:
            await log_ch.send(
                embed=_log_embed(
                    action="Clear",
                    color=0xF1C40F,
                    mod=ctx.author,
                    extra=f"{cantidad} mensajes en {ctx.channel.mention}",
                )
            )

    @commands.hybrid_command(name="kick", description="Expulsa a un miembro")
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        miembro: discord.Member,
        *,
        razon: str | None = None,
    ):
        await miembro.kick(reason=razon)
        await ctx.send(f"👢 {miembro} expulsado. Razón: {razon or 'no especificada'}")
        log_ch = self._log_canal()
        if log_ch:
            await log_ch.send(
                embed=_log_embed(
                    action="Kick", color=0xE67E22, mod=ctx.author, target=miembro, reason=razon
                )
            )

    @commands.hybrid_command(name="ban", description="Banea a un miembro")
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        miembro: discord.Member,
        *,
        razon: str | None = None,
    ):
        await miembro.ban(reason=razon, delete_message_days=0)
        await ctx.send(f"🔨 {miembro} baneado. Razón: {razon or 'no especificada'}")
        log_ch = self._log_canal()
        if log_ch:
            await log_ch.send(
                embed=_log_embed(
                    action="Ban", color=0xE74C3C, mod=ctx.author, target=miembro, reason=razon
                )
            )

    @commands.hybrid_command(name="timeout", description="Silencia temporalmente")
    @commands.has_permissions(moderate_members=True)
    @app_commands.describe(
        miembro="Miembro a silenciar",
        tiempo="Duración (ej. 10m, 1h)",
        razon="Motivo opcional",
    )
    async def timeout(
        self,
        ctx: commands.Context,
        miembro: discord.Member,
        tiempo: str,
        *,
        razon: str | None = None,
    ):
        delta = parse_duration(tiempo)
        if not delta:
            await ctx.send("Formato inválido. Ej. `10m`, `1h30m`.")
            return
        if delta > timedelta(days=28):
            await ctx.send("Máximo 28 días.")
            return
        await miembro.timeout(delta, reason=razon)
        await ctx.send(f"🔇 {miembro} silenciado durante {tiempo}. Razón: {razon or '—'}")
        log_ch = self._log_canal()
        if log_ch:
            await log_ch.send(
                embed=_log_embed(
                    action="Timeout",
                    color=0x9B59B6,
                    mod=ctx.author,
                    target=miembro,
                    reason=razon,
                    extra=f"Duración: {tiempo}",
                )
            )

    @commands.hybrid_command(name="say", description="El bot repite tu mensaje")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx: commands.Context, *, texto: str):
        if ctx.interaction:
            await ctx.send("Mensaje enviado.", ephemeral=True)
            await ctx.channel.send(texto)
        else:
            await ctx.message.delete()
            await ctx.channel.send(texto)

    @kick.error
    @ban.error
    @timeout.error
    @clear.error
    @say.error
    async def perm_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("No tienes permisos para usar este comando.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
