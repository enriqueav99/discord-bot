"""Comandos de utilidad: userinfo, serverinfo, avatar, poll, recordatorio, bug."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("discord.utility")

_DATA_DIR = Path(os.getenv("BOT_DATA_DIR", "."))
_BUGS_FILE = _DATA_DIR / "bugs.json"


def _load_bugs() -> dict:
    if _BUGS_FILE.exists():
        try:
            return json.loads(_BUGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("No se pudo leer %s", _BUGS_FILE)
    return {}


def _save_bugs(data: dict) -> None:
    try:
        _BUGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        log.error("No se pudo guardar bugs.json", exc_info=True)


def _next_bug_id(data: dict, guild_id: int) -> int:
    gk = str(guild_id)
    data.setdefault(gk, {"count": 0})
    data[gk]["count"] += 1
    return data[gk]["count"]


_DURATION_RE = re.compile(r"(?P<n>\d+)(?P<u>[smhd])")


def parse_duration(text: str) -> timedelta | None:
    total = timedelta()
    found = False
    for match in _DURATION_RE.finditer(text.lower()):
        found = True
        n = int(match.group("n"))
        u = match.group("u")
        if u == "s":
            total += timedelta(seconds=n)
        elif u == "m":
            total += timedelta(minutes=n)
        elif u == "h":
            total += timedelta(hours=n)
        elif u == "d":
            total += timedelta(days=n)
    return total if found and total.total_seconds() > 0 else None


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._bugs: dict = _load_bugs()

    @commands.hybrid_command(name="userinfo", description="Información de un usuario")
    @app_commands.describe(miembro="Usuario (default: tú)")
    async def userinfo(self, ctx: commands.Context, miembro: discord.Member | None = None):
        m = miembro or ctx.author
        embed = discord.Embed(title=str(m), color=m.color)
        embed.set_thumbnail(url=m.display_avatar.url)
        embed.add_field(name="ID", value=m.id, inline=True)
        embed.add_field(name="Bot", value="Sí" if m.bot else "No", inline=True)
        embed.add_field(
            name="Cuenta creada",
            value=discord.utils.format_dt(m.created_at, "R"),
            inline=False,
        )
        if isinstance(m, discord.Member) and m.joined_at:
            embed.add_field(
                name="Se unió",
                value=discord.utils.format_dt(m.joined_at, "R"),
                inline=False,
            )
            roles = [r.mention for r in m.roles if r != ctx.guild.default_role]
            if roles:
                embed.add_field(
                    name=f"Roles ({len(roles)})",
                    value=" ".join(roles[:20]),
                    inline=False,
                )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Información del servidor")
    async def serverinfo(self, ctx: commands.Context):
        g = ctx.guild
        if not g:
            return
        embed = discord.Embed(title=g.name, color=0x5865F2)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="ID", value=g.id, inline=True)
        embed.add_field(name="Owner", value=g.owner.mention if g.owner else "?", inline=True)
        embed.add_field(name="Miembros", value=g.member_count, inline=True)
        embed.add_field(name="Canales", value=len(g.channels), inline=True)
        embed.add_field(name="Roles", value=len(g.roles), inline=True)
        embed.add_field(name="Boost", value=f"Tier {g.premium_tier}", inline=True)
        embed.add_field(
            name="Creado",
            value=discord.utils.format_dt(g.created_at, "R"),
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="Avatar de un usuario")
    async def avatar(self, ctx: commands.Context, miembro: discord.Member | None = None):
        m = miembro or ctx.author
        embed = discord.Embed(title=f"Avatar de {m}", color=m.color)
        embed.set_image(url=m.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="poll", description="Crear una encuesta")
    @app_commands.describe(
        pregunta="La pregunta",
        opciones="Opciones separadas por |  (máx 10)",
    )
    async def poll(self, ctx: commands.Context, pregunta: str, *, opciones: str):
        partes = [p.strip() for p in opciones.split("|") if p.strip()]
        if len(partes) < 2 or len(partes) > 10:
            await ctx.send("Necesitas entre 2 y 10 opciones separadas por `|`.")
            return
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        descripcion = "\n".join(f"{emojis[i]} {p}" for i, p in enumerate(partes))
        embed = discord.Embed(title=f"📊 {pregunta}", description=descripcion, color=0x00AAFF)
        embed.set_footer(text=f"Encuesta de {ctx.author}")
        msg = await ctx.send(embed=embed)
        for i in range(len(partes)):
            await msg.add_reaction(emojis[i])

    @commands.hybrid_command(name="recordatorio", description="Te recuerda algo")
    @app_commands.describe(
        tiempo="Duración (ej. 10m, 1h30m, 2d)",
        mensaje="Qué quieres recordar",
    )
    async def recordatorio(self, ctx: commands.Context, tiempo: str, *, mensaje: str):
        delta = parse_duration(tiempo)
        if not delta:
            await ctx.send("Formato inválido. Usa por ej. `10m`, `1h30m`, `2d`.")
            return
        if delta.total_seconds() > 60 * 60 * 24 * 30:
            await ctx.send("Máximo 30 días.")
            return

        when = datetime.now(UTC) + delta
        await ctx.send(f"⏰ Te recordaré {discord.utils.format_dt(when, 'R')}: *{mensaje}*")
        await asyncio.sleep(delta.total_seconds())
        try:
            await ctx.author.send(
                f"⏰ Recordatorio (de hace {tiempo}): {mensaje}\n"
                f"Contexto: {ctx.channel.mention if ctx.guild else 'DM'}"
            )
        except discord.Forbidden:
            await ctx.channel.send(f"{ctx.author.mention} ⏰ {mensaje}")

    @commands.hybrid_command(name="bug", description="Reporta un bug o problema del bot 🐛")
    @app_commands.describe(
        titulo="Resumen breve del problema",
        descripcion="Descripción detallada (pasos para reproducirlo, qué esperabas, qué pasó)",
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def bug(
        self,
        ctx: commands.Context,
        titulo: str,
        *,
        descripcion: str = "Sin descripción adicional.",
    ):
        guild_id = ctx.guild.id if ctx.guild else 0
        bug_id = _next_bug_id(self._bugs, guild_id)
        _save_bugs(self._bugs)

        now = discord.utils.utcnow()
        canal_logs_id = self.bot.config.id_canal_logs
        canal_logs = self.bot.get_channel(canal_logs_id) if canal_logs_id else None

        embed = discord.Embed(
            title=f"🐛 Bug #{bug_id} — {titulo}",
            color=0xE74C3C,
            timestamp=now,
        )
        embed.add_field(name="Descripción", value=descripcion, inline=False)
        embed.add_field(
            name="Reportado por", value=f"{ctx.author.mention} (`{ctx.author}`)", inline=True
        )
        if ctx.guild:
            embed.add_field(name="Servidor", value=ctx.guild.name, inline=True)
        if hasattr(ctx.channel, "mention"):
            embed.add_field(name="Canal", value=ctx.channel.mention, inline=True)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Bug #{bug_id} • {ctx.guild.name if ctx.guild else 'DM'}")

        if canal_logs:
            await canal_logs.send(embed=embed)
            await ctx.send(
                f"✅ Bug **#{bug_id}** enviado al canal de logs. ¡Gracias por el reporte!",
                ephemeral=True,
            )
        else:
            await ctx.send(embed=embed)
            await ctx.send(
                f"✅ Bug **#{bug_id}** registrado. (Configura `DISCORD_ID_CANAL_LOGS` para enviarlo a un canal de auditoría.)",
                ephemeral=True,
            )

    @bug.error
    async def bug_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"Espera {error.retry_after:.0f}s antes de reportar otro bug.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
