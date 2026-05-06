"""Automoderación configurable por servidor."""

from __future__ import annotations

import contextlib
import json
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("discord.automod")

_DATA_DIR = Path(os.getenv("BOT_DATA_DIR", "."))
_AUTOMOD_FILE = _DATA_DIR / "automod.json"


def _load() -> dict:
    if _AUTOMOD_FILE.exists():
        try:
            return json.loads(_AUTOMOD_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("No se pudo leer %s", _AUTOMOD_FILE)
    return {}


def _save(data: dict) -> None:
    try:
        _AUTOMOD_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        log.error("No se pudo guardar automod.json", exc_info=True)


class Automod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._config: dict = _load()

    def _guild_cfg(self, guild_id: int) -> dict:
        return self._config.setdefault(str(guild_id), {"words": [], "max_mentions": 0})

    def _log_canal(self) -> discord.TextChannel | None:
        canal_id = self.bot.config.id_canal_logs
        return self.bot.get_channel(canal_id) if canal_id else None

    # ── listener ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        cfg = self._guild_cfg(message.guild.id)
        reason = None

        content_lower = message.content.lower()
        for word in cfg.get("words", []):
            if word.lower() in content_lower:
                reason = f"palabra prohibida: `{word}`"
                break

        if reason is None:
            max_mentions = cfg.get("max_mentions", 0)
            if max_mentions > 0:
                unique = len({m.id for m in message.mentions if not m.bot})
                if unique > max_mentions:
                    reason = f"demasiadas menciones ({unique} > {max_mentions})"

        if reason is None:
            return

        with contextlib.suppress(discord.HTTPException):
            await message.delete()

        with contextlib.suppress(discord.HTTPException):
            notif = await message.channel.send(
                f"🚫 {message.author.mention} mensaje eliminado por automod ({reason})."
            )
            await notif.delete(delay=5)

        log_ch = self._log_canal()
        if log_ch:
            embed = discord.Embed(title="🤖 Automod — mensaje eliminado", color=0xE74C3C)
            embed.add_field(
                name="Usuario",
                value=f"{message.author.mention} (`{message.author}`)",
                inline=True,
            )
            embed.add_field(name="Canal", value=message.channel.mention, inline=True)
            embed.add_field(name="Razón", value=reason, inline=False)
            if message.content:
                embed.add_field(name="Contenido", value=message.content[:500], inline=False)
            embed.timestamp = discord.utils.utcnow()
            with contextlib.suppress(discord.HTTPException):
                await log_ch.send(embed=embed)

    # ── /automod ─────────────────────────────────────────────────────────────

    @commands.hybrid_group(name="automod", description="Configura el automoderador 🤖")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def automod_cmd(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            cfg = self._guild_cfg(ctx.guild.id)
            words = cfg.get("words", [])
            max_m = cfg.get("max_mentions", 0)
            embed = discord.Embed(title="🤖 Configuración Automod", color=0x3498DB)
            embed.add_field(
                name="Palabras prohibidas",
                value=", ".join(f"`{w}`" for w in words) or "ninguna",
                inline=False,
            )
            embed.add_field(
                name="Máx. menciones",
                value=str(max_m) if max_m > 0 else "desactivado",
                inline=True,
            )
            await ctx.send(embed=embed, ephemeral=True)

    @automod_cmd.command(name="add", description="Añade una palabra a la lista negra")
    @app_commands.describe(palabra="Palabra o frase a prohibir")
    async def automod_add(self, ctx: commands.Context, *, palabra: str):
        cfg = self._guild_cfg(ctx.guild.id)
        word = palabra.lower().strip()
        if word in cfg["words"]:
            await ctx.send(f"`{word}` ya está en la lista.", ephemeral=True)
            return
        cfg["words"].append(word)
        _save(self._config)
        await ctx.send(f"✅ `{word}` añadida a la lista negra.", ephemeral=True)

    @automod_cmd.command(name="remove", description="Elimina una palabra de la lista negra")
    @app_commands.describe(palabra="Palabra a eliminar")
    async def automod_remove(self, ctx: commands.Context, *, palabra: str):
        cfg = self._guild_cfg(ctx.guild.id)
        word = palabra.lower().strip()
        if word not in cfg["words"]:
            await ctx.send(f"`{word}` no está en la lista.", ephemeral=True)
            return
        cfg["words"].remove(word)
        _save(self._config)
        await ctx.send(f"🗑️ `{word}` eliminada de la lista negra.", ephemeral=True)

    @automod_cmd.command(name="list", description="Muestra la configuración del automod")
    async def automod_list(self, ctx: commands.Context):
        cfg = self._guild_cfg(ctx.guild.id)
        words = cfg.get("words", [])
        max_m = cfg.get("max_mentions", 0)
        embed = discord.Embed(title="🤖 Automod", color=0x3498DB)
        embed.add_field(
            name="Palabras prohibidas",
            value="\n".join(f"• `{w}`" for w in words) or "ninguna",
            inline=False,
        )
        embed.add_field(
            name="Máx. menciones",
            value=str(max_m) if max_m > 0 else "desactivado",
            inline=True,
        )
        await ctx.send(embed=embed, ephemeral=True)

    @automod_cmd.command(
        name="menciones",
        description="Máximo de menciones por mensaje (0 = desactivado)",
    )
    @app_commands.describe(maximo="Número máximo permitido (0 = off)")
    async def automod_menciones(self, ctx: commands.Context, maximo: int):
        if maximo < 0:
            await ctx.send("El valor mínimo es 0 (desactivado).", ephemeral=True)
            return
        cfg = self._guild_cfg(ctx.guild.id)
        cfg["max_mentions"] = maximo
        _save(self._config)
        if maximo == 0:
            await ctx.send("🔕 Límite de menciones desactivado.", ephemeral=True)
        else:
            await ctx.send(f"✅ Máximo de menciones por mensaje: **{maximo}**.", ephemeral=True)

    @automod_cmd.error
    async def automod_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Necesitas el permiso `Gestionar servidor`.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Automod(bot))
