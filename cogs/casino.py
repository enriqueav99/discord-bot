"""Comandos de casino: ruleta con fichas virtuales."""

from __future__ import annotations

import asyncio
import random
from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands

# Números rojos en la ruleta europea estándar
_ROJOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

_FICHAS_INICIALES = 1000
_APUESTA_DEFAULT = 100
_RECARGA = 500
_COOLDOWN_RECARGA_H = 6


def _color_emoji(n: int) -> str:
    if n == 0:
        return "🟢"
    return "🔴" if n in _ROJOS else "⚫"


def _parse_apuesta(texto: str) -> tuple[str, int | None] | None:
    """Devuelve (tipo, numero_o_None) o None si la apuesta es inválida."""
    t = texto.lower().strip()
    if t in ("rojo", "negro", "verde", "par", "impar", "alto", "bajo"):
        return (t, None)
    try:
        n = int(t)
        if 0 <= n <= 36:
            return ("numero", n)
    except ValueError:
        pass
    return None


def _evaluar(numero: int, tipo: str, objetivo: int | None) -> tuple[bool, int]:
    """Devuelve (ganó, multiplicador_de_ganancia).
    La ganancia neta es apuesta × multiplicador; el número total devuelto
    en casino sería apuesta × (multiplicador + 1).
    """
    match tipo:
        case "numero":
            return numero == objetivo, 35
        case "rojo":
            return numero in _ROJOS, 1
        case "negro":
            return numero not in _ROJOS and numero != 0, 1
        case "verde":
            return numero == 0, 35
        case "par":
            return numero != 0 and numero % 2 == 0, 1
        case "impar":
            return numero != 0 and numero % 2 == 1, 1
        case "alto":
            return 19 <= numero <= 36, 1
        case "bajo":
            return 1 <= numero <= 18, 1
    return False, 0


class Casino(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # _fichas[guild_id][user_id] = saldo; primer acceso inicia en _FICHAS_INICIALES
        self._fichas: dict[int, dict[int, int]] = defaultdict(
            lambda: defaultdict(lambda: _FICHAS_INICIALES)
        )

    def _saldo(self, guild_id: int, user_id: int) -> int:
        return self._fichas[guild_id][user_id]

    # ── /ruleta ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="ruleta", description="Apuesta en la ruleta del casino 🎰")
    @app_commands.describe(
        apuesta="rojo · negro · verde · par · impar · alto · bajo · o un número (0-36)",
        cantidad="Fichas a apostar (default 100)",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ruleta(
        self,
        ctx: commands.Context,
        apuesta: str,
        cantidad: int = _APUESTA_DEFAULT,
    ):
        parsed = _parse_apuesta(apuesta)
        if parsed is None:
            await ctx.send(
                "Apuesta inválida. Usa: `rojo`, `negro`, `verde`, `par`, `impar`, "
                "`alto`, `bajo` o un número del **0 al 36**.",
                ephemeral=True,
            )
            return

        if cantidad < 1:
            await ctx.send("La apuesta mínima es **1** ficha.", ephemeral=True)
            return

        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self._saldo(guild_id, ctx.author.id)

        if cantidad > saldo:
            await ctx.send(
                f"No tienes suficientes fichas. Saldo: **{saldo}** 🪙  "
                f"— usa `/recargar` si te quedaste sin fichas.",
                ephemeral=True,
            )
            return

        tipo, objetivo = parsed

        # Animación de giro
        msg = await ctx.send("🎰 Lanzando la bola...")
        await asyncio.sleep(0.8)
        await msg.edit(content="🎰 ⬛🔴⬛🔴🟢⬛🔴⬛ girando...")
        await asyncio.sleep(0.8)

        numero = random.randint(0, 36)
        gano, mult = _evaluar(numero, tipo, objetivo)

        if gano:
            ganancia = cantidad * mult
            self._fichas[guild_id][ctx.author.id] += ganancia
            nuevo_saldo = self._saldo(guild_id, ctx.author.id)
            embed = discord.Embed(
                title=f"{_color_emoji(numero)} **{numero}** — ¡Ganaste! 🎉",
                description=f"+**{ganancia}** fichas",
                color=discord.Color.green(),
            )
            embed.add_field(name="Apuesta", value=f"`{apuesta}` × {cantidad} 🪙", inline=True)
            embed.add_field(name="Pago", value=f"×{mult + 1}", inline=True)
        else:
            self._fichas[guild_id][ctx.author.id] -= cantidad
            nuevo_saldo = self._saldo(guild_id, ctx.author.id)
            embed = discord.Embed(
                title=f"{_color_emoji(numero)} **{numero}** — Perdiste",
                description=f"-**{cantidad}** fichas",
                color=discord.Color.red(),
            )
            embed.add_field(name="Apuesta", value=f"`{apuesta}` × {cantidad} 🪙", inline=True)

        embed.add_field(name="Saldo", value=f"**{nuevo_saldo}** 🪙", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await msg.edit(content=None, embed=embed)

    @ruleta.error
    async def ruleta_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Espera {error.retry_after:.1f}s.", ephemeral=True)

    # ── /fichas ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="fichas", description="Consulta tu saldo de fichas 🪙")
    async def fichas_cmd(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self._saldo(guild_id, ctx.author.id)
        await ctx.send(f"{ctx.author.mention} tiene **{saldo}** fichas 🪙")

    # ── /recargar ────────────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="recargar", description=f"Recibe {_RECARGA} fichas gratis (cada {_COOLDOWN_RECARGA_H}h) 🎁"
    )
    @commands.cooldown(1, _COOLDOWN_RECARGA_H * 3600, commands.BucketType.user)
    async def recargar(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        self._fichas[guild_id][ctx.author.id] += _RECARGA
        nuevo = self._saldo(guild_id, ctx.author.id)
        await ctx.send(
            f"🎁 {ctx.author.mention} recibió **{_RECARGA}** fichas. Saldo: **{nuevo}** 🪙"
        )

    @recargar.error
    async def recargar_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            horas = int(error.retry_after // 3600)
            minutos = int((error.retry_after % 3600) // 60)
            tiempo = f"{horas}h {minutos}m" if horas else f"{minutos}m"
            await ctx.send(f"Ya recargaste hace poco. Vuelve en **{tiempo}**.", ephemeral=True)

    # ── /ranking_fichas ──────────────────────────────────────────────────────

    @commands.hybrid_command(name="ranking_fichas", description="Top de fichas en el servidor 🏆")
    async def ranking_fichas(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        scores = dict(self._fichas.get(guild_id, {}))
        if not scores:
            await ctx.send("Nadie ha jugado todavía. ¡Usa `/ruleta`!")
            return
        top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:10]
        medallas = ["🥇", "🥈", "🥉"]
        lineas = []
        for i, (uid, saldo) in enumerate(top):
            member = ctx.guild.get_member(uid) if ctx.guild else None
            nombre = member.display_name if member else f"<usuario {uid}>"
            prefijo = medallas[i] if i < 3 else f"`{i + 1}.`"
            lineas.append(f"{prefijo} **{nombre}** — {saldo} 🪙")
        embed = discord.Embed(
            title="🏆 Ranking de fichas",
            description="\n".join(lineas),
            color=0xFFD700,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Casino(bot))
