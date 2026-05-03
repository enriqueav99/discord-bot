"""Comandos generales del bot."""

from __future__ import annotations

import platform

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

    @commands.hybrid_command(name="docs", description="Guía rápida de uso del bot")
    async def docs(self, ctx: commands.Context):
        prefix = self.bot.config.prefix
        embed = discord.Embed(
            title="📚 Guía del Bot de Korea",
            description=(
                f"Los comandos funcionan como slash (`/comando`) "
                f"o con prefijo (`{prefix}comando`).\n"
                "Usa `/help` para ver la lista completa con parámetros."
            ),
            color=0x00AAFF,
        )
        embed.add_field(
            name="🎵 Música",
            value="`play`, `playnext`, `queue`, `skip`, `loop`, `shuffle`, `autoplay`, `nowplaying`, `lyrics`",
            inline=False,
        )
        embed.add_field(name="🎮 Juegos", value="`adivina`, `trivia`, `pokeranking`", inline=False)
        embed.add_field(
            name="🎂 Cumpleaños", value="`cumple set`, `cumple del`, `cumple lista`", inline=False
        )
        embed.add_field(
            name="🛠️ Utilidad",
            value="`poll`, `recordatorio`, `userinfo`, `serverinfo`, `avatar`",
            inline=False,
        )
        embed.add_field(
            name="🔨 Moderación", value="`kick`, `ban`, `timeout`, `clear`", inline=False
        )
        embed.add_field(
            name="🔗 Código fuente",
            value="[github.com/enriqueav99/discord-bot](https://github.com/enriqueav99/discord-bot)",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="stats", description="Estadísticas del bot")
    async def stats(self, ctx: commands.Context):
        uptime = discord.utils.utcnow() - self.bot.start_time
        days = uptime.days
        hours, rem = divmod(uptime.seconds, 3600)
        minutes = rem // 60
        guilds = len(self.bot.guilds)
        users = sum(g.member_count or 0 for g in self.bot.guilds)

        embed = discord.Embed(title="📊 Estadísticas", color=0x00AAFF)
        embed.add_field(name="Servidores", value=str(guilds), inline=True)
        embed.add_field(name="Usuarios", value=str(users), inline=True)
        embed.add_field(name="Latencia", value=f"{round(self.bot.latency * 1000)} ms", inline=True)
        embed.add_field(name="Uptime", value=f"{days}d {hours}h {minutes}m", inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="invite", description="Genera un link para invitar al bot")
    async def invite(self, ctx: commands.Context):
        perms = discord.Permissions(
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            manage_messages=True,
            connect=True,
            speak=True,
            kick_members=True,
            ban_members=True,
            moderate_members=True,
        )
        url = discord.utils.oauth_url(self.bot.user.id, permissions=perms)
        embed = discord.Embed(
            title="🔗 Invitar al bot",
            description=f"[Haz clic aquí para añadir el Bot de Korea a tu servidor]({url})",
            color=0x00AAFF,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
