"""Comandos generales del bot."""

from __future__ import annotations

import contextlib
import platform
import re

import discord
from discord import app_commands
from discord.ext import commands

from src.info import definir_info

# (cog_name, emoji, label_es)
_COGS = [
    ("General", "⚙️", "General"),
    ("Music", "🎵", "Música"),
    ("Lyrics", "🎤", "Letras"),
    ("Birthdays", "🎂", "Cumpleaños"),
    ("Voice", "🔊", "Voz"),
    ("Fun", "🎲", "Diversión"),
    ("Games", "🎮", "Juegos"),
    ("Casino", "🎰", "Casino"),
    ("Utility", "🛠️", "Utilidad"),
    ("Moderation", "🔨", "Moderación"),
]
_COG_EMOJI = {name: emoji for name, emoji, _ in _COGS}
_COG_LABEL = {name: label for name, _, label in _COGS}


# ── helpers ──────────────────────────────────────────────────────────────────


def _prefix_sig(sig: str) -> str:
    """Quita los <> de los args requeridos para la versión de prefix.
    Evita que <prefix<arg>> quede confuso con prefijos como '<'.
    """
    return re.sub(r"<([^>]+)>", r"\1", sig)


def _cmd_lines(cog: commands.Cog, prefix: str) -> list[str]:
    lines = []
    for cmd in sorted(cog.get_commands(), key=lambda c: c.name):
        if cmd.hidden:
            continue
        if isinstance(cmd, commands.Group):
            lines.append(f"`{prefix}{cmd.name}` — {cmd.description or '—'}")
            for sub in sorted(cmd.commands, key=lambda c: c.name):
                if not sub.hidden:
                    sig = f" {sub.signature}" if sub.signature else ""
                    lines.append(f"  ↳ `{cmd.name} {sub.name}{sig}` — {sub.description or '—'}")
        else:
            sig = f" {_prefix_sig(cmd.signature)}" if cmd.signature else ""
            lines.append(f"`{prefix}{cmd.name}{sig}` — {cmd.description or '—'}")
    return lines


def _overview_embed(bot: commands.Bot, prefix: str) -> discord.Embed:
    embed = discord.Embed(
        title="📖 Ayuda del Bot",
        description=(
            "Elige una categoría en el menú de abajo, "
            "o usa `/help <comando>` para información detallada de un comando.\n"
            f"Los comandos funcionan como `/comando` o `{prefix}comando`."
        ),
        color=0x00AAFF,
    )
    for cog_name, emoji, label in _COGS:
        cog = bot.cogs.get(cog_name)
        if not cog:
            continue
        names = [
            f"`{c.name}`" for c in sorted(cog.get_commands(), key=lambda c: c.name) if not c.hidden
        ]
        if names:
            embed.add_field(name=f"{emoji} {label}", value=" ".join(names), inline=True)
    embed.set_footer(text=f"Prefix: {prefix}  •  /help <comando> para detalles")
    return embed


def _cog_embed(cog: commands.Cog, cog_name: str, prefix: str) -> discord.Embed:
    emoji = _COG_EMOJI.get(cog_name, "📦")
    label = _COG_LABEL.get(cog_name, cog_name)
    lines = _cmd_lines(cog, prefix)
    embed = discord.Embed(
        title=f"{emoji} {label}",
        description="\n".join(lines) or "Sin comandos.",
        color=0x00AAFF,
    )
    embed.set_footer(text=f"Prefix: {prefix}  •  /help <comando> para detalles")
    return embed


def _detail_embed(cmd: commands.Command | commands.Group, prefix: str) -> discord.Embed:
    cog_name = cmd.cog.__class__.__name__ if cmd.cog else ""
    emoji = _COG_EMOJI.get(cog_name, "📦")
    embed = discord.Embed(
        title=f"{emoji} `{cmd.qualified_name}`",
        description=cmd.description or cmd.brief or "Sin descripción.",
        color=0x00AAFF,
    )

    if isinstance(cmd, commands.Group):
        subs = [s for s in sorted(cmd.commands, key=lambda c: c.name) if not s.hidden]
        if subs:
            lines = []
            for sub in subs:
                sig = f" {sub.signature}" if sub.signature else ""
                lines.append(f"`{cmd.name} {sub.name}{sig}` — {sub.description or '—'}")
            embed.add_field(name="Subcomandos", value="\n".join(lines), inline=False)
    else:
        sig = cmd.signature or ""
        embed.add_field(
            name="Uso",
            value=(
                f"`/{cmd.qualified_name}{' ' + sig if sig else ''}`\n"
                f"`{prefix}{cmd.qualified_name}{' ' + _prefix_sig(sig) if sig else ''}`"
            ),
            inline=False,
        )
        try:
            cd = cmd._buckets._cooldown
            if cd:
                embed.add_field(
                    name="Cooldown",
                    value=f"{cd.rate} uso{'s' if cd.rate != 1 else ''} / {cd.per:.0f}s",
                    inline=True,
                )
        except AttributeError:
            pass

    if cmd.aliases:
        embed.add_field(name="Alias", value=", ".join(f"`{a}`" for a in cmd.aliases), inline=True)
    embed.set_footer(text=f"Categoría: {_COG_LABEL.get(cog_name, cog_name)}")
    return embed


# ── View ─────────────────────────────────────────────────────────────────────


class _HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, prefix: str):
        self._bot = bot
        self._prefix = prefix
        options = [
            discord.SelectOption(label=label, value=cog_name, emoji=emoji)
            for cog_name, emoji, label in _COGS
            if bot.cogs.get(cog_name)
        ]
        super().__init__(placeholder="Elige una categoría...", options=options)

    async def callback(self, interaction: discord.Interaction):
        cog = self._bot.cogs.get(self.values[0])
        if not cog:
            await interaction.response.send_message("Categoría no disponible.", ephemeral=True)
            return
        await interaction.response.edit_message(embed=_cog_embed(cog, self.values[0], self._prefix))


class _HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, prefix: str):
        super().__init__(timeout=120)
        self.message: discord.Message | None = None
        self.add_item(_HelpSelect(bot, prefix))

    async def on_timeout(self):
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=None)


# ── Cog ──────────────────────────────────────────────────────────────────────


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

    @commands.hybrid_command(name="help", description="Ayuda y lista de comandos")
    @app_commands.describe(comando="Comando específico del que obtener información")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help_cmd(self, ctx: commands.Context, *, comando: str | None = None):
        prefix = self.bot.config.prefix
        if comando:
            cmd = self.bot.get_command(comando.lower())
            if cmd is None or cmd.hidden:
                await ctx.send(f"Comando `{comando}` no encontrado.", ephemeral=True)
                return
            await ctx.send(embed=_detail_embed(cmd, prefix))
        else:
            view = _HelpView(self.bot, prefix)
            view.message = await ctx.send(embed=_overview_embed(self.bot, prefix), view=view)

    @help_cmd.autocomplete("comando")
    async def _help_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        results: list[app_commands.Choice[str]] = []
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue
            if current.lower() in cmd.name:
                results.append(app_commands.Choice(name=cmd.name, value=cmd.name))
            if isinstance(cmd, commands.Group):
                for sub in cmd.commands:
                    if not sub.hidden:
                        full = f"{cmd.name} {sub.name}"
                        if current.lower() in full:
                            results.append(app_commands.Choice(name=full, value=full))
        return sorted(results, key=lambda c: c.name)[:25]

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
            view_channel=True,
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
            description=f"[Haz clic aquí para añadir el bot a tu servidor]({url})",
            color=0x00AAFF,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
