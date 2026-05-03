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
        await ctx.send("¡Hola!")

    @commands.hybrid_command(name="info", description="Información del bot")
    async def info(self, ctx: commands.Context):
        await ctx.send(embed=definir_info())

    @commands.hybrid_command(name="help", description="Lista de comandos con descripción")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help_cmd(self, ctx: commands.Context):
        prefix = self.bot.config.prefix

        COG_LABELS = {
            "General": "⚙️ General",
            "Music": "🎵 Música",
            "Lyrics": "🎤 Letras",
            "Birthdays": "🎂 Cumpleaños",
            "Voice": "🔊 Voz",
            "Fun": "🎲 Diversión",
            "Games": "🎮 Juegos",
            "Utility": "🛠️ Utilidad",
            "Moderation": "🔨 Moderación",
        }

        def _fmt(name: str, sig: str, desc: str, indent: str = "") -> str:
            usage = f"{prefix}{name}" + (f" {sig}" if sig else "")
            return f"{indent}`{usage}` — {desc}"

        embed = discord.Embed(title="📖 Comandos del Bot de Korea", color=0x00AAFF)

        for cog_name, label in COG_LABELS.items():
            cog = self.bot.cogs.get(cog_name)
            if not cog:
                continue
            lines = []
            for cmd in sorted(cog.get_commands(), key=lambda c: c.name):
                if cmd.hidden:
                    continue
                if isinstance(cmd, commands.Group):
                    lines.append(_fmt(cmd.name, "", cmd.description or ""))
                    for sub in sorted(cmd.commands, key=lambda c: c.name):
                        if sub.hidden:
                            continue
                        lines.append(
                            _fmt(
                                f"{cmd.name} {sub.name}", sub.signature, sub.description or "", "  "
                            )
                        )
                else:
                    lines.append(_fmt(cmd.name, cmd.signature, cmd.description or ""))
            if lines:
                value = "\n".join(lines)
                if len(value) > 1024:
                    value = value[:1021] + "..."
                embed.add_field(name=label, value=value, inline=False)

        embed.set_footer(text=f"Prefix: {prefix} • también disponibles como /comando")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
