"""Sistema de cumpleaños: registro y anuncios automáticos."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

log = logging.getLogger("discord.birthdays")

BIRTHDAY_FILE = Path("birthdays.json")


def _load() -> dict:
    if BIRTHDAY_FILE.exists():
        try:
            return json.loads(BIRTHDAY_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("No se pudo leer %s, empezando vacío", BIRTHDAY_FILE)
    return {}


def _save(data: dict) -> None:
    BIRTHDAY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class Birthdays(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._data: dict = _load()  # {guild_id: {user_id: "MM-DD"}}
        self._announced: set[tuple] = set()  # (guild_id, user_id, "MM-DD") anunciados hoy
        self.daily_check.start()

    def cog_unload(self):
        self.daily_check.cancel()

    def _guild(self, guild_id: int) -> dict:
        key = str(guild_id)
        if key not in self._data:
            self._data[key] = {}
        return self._data[key]

    @commands.hybrid_group(name="cumple", description="Gestión de cumpleaños")
    async def cumple(self, ctx: commands.Context):
        pass

    @cumple.command(name="set", description="Registra tu cumpleaños (DD/MM)")
    @app_commands.describe(fecha="Día y mes, ej. 25/12")
    async def set_birthday(self, ctx: commands.Context, fecha: str):
        try:
            parts = fecha.replace("-", "/").split("/")
            day, month = int(parts[0]), int(parts[1])
            date(2000, month, day)  # valida que la fecha exista
        except (ValueError, IndexError):
            await ctx.send("Formato inválido. Usa DD/MM, por ej. `25/12`.")
            return
        guild_data = self._guild(ctx.guild.id)
        guild_data[str(ctx.author.id)] = f"{month:02d}-{day:02d}"
        _save(self._data)
        await ctx.send(f"🎂 Cumpleaños registrado: **{day:02d}/{month:02d}**.")

    @cumple.command(name="del", description="Elimina tu cumpleaños registrado")
    async def del_birthday(self, ctx: commands.Context):
        guild_data = self._guild(ctx.guild.id)
        if str(ctx.author.id) not in guild_data:
            await ctx.send("No tienes ningún cumpleaños registrado.")
            return
        del guild_data[str(ctx.author.id)]
        _save(self._data)
        await ctx.send("🗑️ Cumpleaños eliminado.")

    @cumple.command(name="lista", description="Muestra los próximos cumpleaños del servidor")
    async def lista(self, ctx: commands.Context):
        guild_data = self._guild(ctx.guild.id)
        if not guild_data:
            await ctx.send(
                "No hay cumpleaños registrados. Usa `cumple set DD/MM` para añadir el tuyo."
            )
            return

        today = date.today()
        entries = []
        for user_id_str, mmdd in guild_data.items():
            month, day = int(mmdd[:2]), int(mmdd[3:])
            member = ctx.guild.get_member(int(user_id_str))
            name = member.display_name if member else f"<@{user_id_str}>"
            bd = date(today.year, month, day)
            if bd < today:
                bd = date(today.year + 1, month, day)
            days_left = (bd - today).days
            entries.append((days_left, day, month, name))

        entries.sort()
        lines = []
        for days_left, day, month, name in entries[:20]:
            hoy = " 🎉 **¡HOY!**" if days_left == 0 else f" (en {days_left}d)"
            lines.append(f"`{day:02d}/{month:02d}` — **{name}**{hoy}")

        embed = discord.Embed(title="🎂 Cumpleaños", description="\n".join(lines), color=0xFF69B4)
        embed.set_footer(text="Usa 'cumple set DD/MM' para registrar el tuyo")
        await ctx.send(embed=embed)

    @tasks.loop(hours=1)
    async def daily_check(self):
        today = date.today()
        today_mmdd = f"{today.month:02d}-{today.day:02d}"

        # Limpiar anuncios de días anteriores
        self._announced = {k for k in self._announced if k[2] == today_mmdd}

        for guild_id_str, guild_data in self._data.items():
            guild = self.bot.get_guild(int(guild_id_str))
            if not guild:
                continue
            canal = self.bot.get_channel(self.bot.config.id_canal_principal)
            if not canal:
                continue

            for user_id_str, mmdd in guild_data.items():
                if mmdd != today_mmdd:
                    continue
                key = (guild_id_str, user_id_str, today_mmdd)
                if key in self._announced:
                    continue
                self._announced.add(key)
                member = guild.get_member(int(user_id_str))
                mention = member.mention if member else f"<@{user_id_str}>"
                await canal.send(f"🎂 ¡Hoy es el cumpleaños de {mention}! 🎉")

    @daily_check.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Birthdays(bot))
