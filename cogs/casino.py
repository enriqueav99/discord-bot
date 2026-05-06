"""Comandos de casino: ruleta con fichas persistentes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("discord.casino")

_DATA_DIR = Path(os.getenv("BOT_DATA_DIR", "."))
_FICHAS_FILE = _DATA_DIR / "fichas.json"

_ROJOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
_FICHAS_INICIALES = 1000
_APUESTA_DEFAULT = 100
_RECARGA = 500
_COOLDOWN_RECARGA_H = 6
_MAX_APUESTAS = 8

# Tragaperras — símbolos ordenados de más a menos frecuente
_SLOTS = ["🍒", "🍒", "🍒", "🍋", "🍋", "🍊", "🍊", "🍇", "🔔", "💎", "7️⃣"]
_SLOT_MULT = {"🍒": 3, "🍋": 5, "🍊": 8, "🍇": 12, "🔔": 20, "💎": 40, "7️⃣": 75}

# Orden real de la ruleta europea (sentido horario)
_WHEEL = [
    0,
    32,
    15,
    19,
    4,
    21,
    2,
    25,
    17,
    34,
    6,
    27,
    13,
    36,
    11,
    30,
    8,
    23,
    10,
    5,
    24,
    16,
    33,
    1,
    20,
    14,
    31,
    9,
    22,
    18,
    29,
    7,
    28,
    12,
    35,
    3,
    26,
]


def _load() -> dict[str, dict[str, int]]:
    if _FICHAS_FILE.exists():
        try:
            return json.loads(_FICHAS_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("No se pudo leer %s, empezando vacío", _FICHAS_FILE)
    return {}


def _save(data: dict[str, dict[str, int]]) -> None:
    try:
        _FICHAS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        log.error("No se pudo guardar fichas.json", exc_info=True)


def _color_emoji(n: int) -> str:
    if n == 0:
        return "🟢"
    return "🔴" if n in _ROJOS else "⚫"


def _wheel_display(numero: int) -> str:
    """7 números de la noria centrados en el ganador, con flechas."""
    idx = _WHEEL.index(numero)
    n = len(_WHEEL)
    window = [_WHEEL[(idx - 3 + i) % n] for i in range(7)]
    parts = []
    for i, num in enumerate(window):
        e = _color_emoji(num)
        parts.append(f"**▶{e}{num}◀**" if i == 3 else f"{e}{num}")
    return "  ".join(parts)


def _parse_apuestas(
    texto: str, default_cantidad: int
) -> tuple[list[tuple[str, int | None, int]], list[str]]:
    """Parse 'bet1 [amount1] bet2 [amount2] …' from a single string.

    An integer ≥ 1 immediately following a bet token is consumed as that
    bet's per-bet amount; otherwise default_cantidad is used.
    Returns (valid_bets, invalid_tokens).  Each valid bet is (tipo, objetivo, cantidad).
    """
    tokens = re.split(r"[\s,]+", texto.strip())
    valid: list[tuple[str, int | None, int]] = []
    invalid: list[str] = []
    seen: set[tuple[str, int | None]] = set()
    pending: tuple[str, int | None] | None = None

    for token in tokens:
        if not token:
            continue
        if pending is not None:
            try:
                n = int(token)
                if n >= 1:
                    key = pending
                    if key not in seen:
                        seen.add(key)
                        valid.append((pending[0], pending[1], n))
                    pending = None
                    continue
                # n == 0: fall through → treat "0" as a new bet on number 0
                # n < 0: fall through → _parse_apuesta will return None → invalid
            except ValueError:
                pass  # not an integer; fall through to bet parsing
        result = _parse_apuesta(token)
        if result is not None:
            if pending is not None:
                key = pending
                if key not in seen:
                    seen.add(key)
                    valid.append((pending[0], pending[1], default_cantidad))
            pending = result
        else:
            invalid.append(token)
    if pending is not None:
        key = pending
        if key not in seen:
            seen.add(key)
            valid.append((pending[0], pending[1], default_cantidad))
    return valid, invalid


def _parse_apuesta(texto: str) -> tuple[str, int | None] | None:
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
        self._fichas: dict[str, dict[str, int]] = _load()

    def _saldo(self, guild_id: int, user_id: int) -> int:
        return self._fichas.get(str(guild_id), {}).get(str(user_id), _FICHAS_INICIALES)

    def _ajustar(self, guild_id: int, user_id: int, delta: int) -> int:
        gk, uk = str(guild_id), str(user_id)
        actual = self._fichas.setdefault(gk, {}).get(uk, _FICHAS_INICIALES)
        nuevo = max(0, actual + delta)
        self._fichas[gk][uk] = nuevo
        _save(self._fichas)
        return nuevo

    # ── /ruleta ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="ruleta", description="Apuesta en la ruleta del casino 🎰")
    @commands.guild_only()
    @app_commands.describe(
        apuestas="apuestas con cantidad opcional: 'rojo 50 par bajo 4 20 rojo 0-36 …'",
        cantidad="Fichas por defecto para apuestas sin cantidad explícita (default 100)",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ruleta(
        self,
        ctx: commands.Context,
        apuestas: str,
        cantidad: int = _APUESTA_DEFAULT,
    ):
        if cantidad < 1:
            await ctx.send("La apuesta mínima es **1** ficha.", ephemeral=True)
            return

        validas, invalidas = _parse_apuestas(apuestas, cantidad)

        if invalidas:
            await ctx.send(
                f"Apuesta(s) inválida(s): `{'`, `'.join(invalidas)}`.\n"
                "Usa: `rojo`, `negro`, `verde`, `par`, `impar`, `alto`, `bajo` o un número **0-36**,\n"
                "opcionalmente seguido de la cantidad: `rojo 50 par bajo 4 20`.",
                ephemeral=True,
            )
            return

        if not validas:
            await ctx.send(
                "Indica al menos una apuesta: `rojo`, `negro`, `verde`, `par`, `impar`, "
                "`alto`, `bajo` o un número del **0 al 36**.",
                ephemeral=True,
            )
            return

        if len(validas) > _MAX_APUESTAS:
            await ctx.send(f"Máximo {_MAX_APUESTAS} apuestas simultáneas.", ephemeral=True)
            return

        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self._saldo(guild_id, ctx.author.id)
        coste_total = sum(bet[2] for bet in validas)

        if coste_total > saldo:
            desglose = " + ".join(str(bet[2]) for bet in validas)
            await ctx.send(
                f"No tienes suficientes fichas. Necesitas **{coste_total}** 🪙 "
                f"({desglose}), saldo: **{saldo}** 🪙\n"
                "Usa `/recargar` si te quedaste sin fichas.",
                ephemeral=True,
            )
            return

        msg = await ctx.send("🎰 Lanzando la bola...")
        await asyncio.sleep(0.7)
        await msg.edit(content="🎡 ⚫🔴⬛🔴🟢🔴⚫ girando...")
        await asyncio.sleep(0.8)

        numero = random.randint(0, 36)

        delta_total = 0
        lineas = []
        for tipo, objetivo, bet_cantidad in validas:
            gano, mult = _evaluar(numero, tipo, objetivo)
            etiqueta = str(objetivo) if tipo == "numero" else tipo
            if gano:
                delta_total += bet_cantidad * mult
                lineas.append(
                    f"✅ `{etiqueta}` **{bet_cantidad}**×{mult + 1} → +**{bet_cantidad * mult}** 🪙"
                )
            else:
                delta_total -= bet_cantidad
                lineas.append(f"❌ `{etiqueta}` **{bet_cantidad}** → -**{bet_cantidad}** 🪙")

        nuevo_saldo = self._ajustar(guild_id, ctx.author.id, delta_total)

        if delta_total > 0:
            titulo = f"{_color_emoji(numero)} {numero} — ¡Ganaste! 🎉"
            color = discord.Color.green()
        elif delta_total < 0:
            titulo = f"{_color_emoji(numero)} {numero} — Perdiste"
            color = discord.Color.red()
        else:
            titulo = f"{_color_emoji(numero)} {numero} — Empate"
            color = discord.Color.greyple()

        embed = discord.Embed(title=titulo, description=_wheel_display(numero), color=color)
        embed.add_field(name="Resultados", value="\n".join(lineas), inline=False)
        signo = "+" if delta_total >= 0 else ""
        embed.add_field(name="Neto", value=f"{signo}**{delta_total}** 🪙", inline=True)
        embed.add_field(name="Saldo", value=f"**{nuevo_saldo}** 🪙", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await msg.edit(content=None, embed=embed)

    @ruleta.error
    async def ruleta_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Espera {error.retry_after:.1f}s.", ephemeral=True)

    # ── /fichas ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="fichas", description="Consulta tu saldo de fichas 🪙")
    @commands.guild_only()
    async def fichas_cmd(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self._saldo(guild_id, ctx.author.id)
        await ctx.send(f"{ctx.author.mention} tiene **{saldo}** fichas 🪙")

    # ── /recargar ────────────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="recargar",
        description=f"Recibe {_RECARGA} fichas gratis (cada {_COOLDOWN_RECARGA_H}h) 🎁",
    )
    @commands.guild_only()
    @commands.cooldown(1, _COOLDOWN_RECARGA_H * 3600, commands.BucketType.member)
    async def recargar(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        nuevo = self._ajustar(guild_id, ctx.author.id, _RECARGA)
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
    @commands.guild_only()
    async def ranking_fichas(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        scores = self._fichas.get(str(guild_id), {})
        if not scores:
            await ctx.send("Nadie ha jugado todavía. ¡Usa `/ruleta`!")
            return
        top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:10]
        medallas = ["🥇", "🥈", "🥉"]
        lineas = []
        for i, (uid_str, saldo) in enumerate(top):
            member = ctx.guild.get_member(int(uid_str)) if ctx.guild else None
            nombre = member.display_name if member else f"<usuario {uid_str}>"
            prefijo = medallas[i] if i < 3 else f"`{i + 1}.`"
            lineas.append(f"{prefijo} **{nombre}** — {saldo} 🪙")
        embed = discord.Embed(
            title="🏆 Ranking de fichas",
            description="\n".join(lineas),
            color=0xFFD700,
        )
        await ctx.send(embed=embed)

    # ── /doble ───────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="doble", description="Cara o cruz: dobla o pierde tus fichas 🪙")
    @commands.guild_only()
    @app_commands.describe(cantidad="Fichas a apostar (default 100)")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def doble(self, ctx: commands.Context, cantidad: int = _APUESTA_DEFAULT):
        if cantidad < 1:
            await ctx.send("La apuesta mínima es **1** ficha.", ephemeral=True)
            return

        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self._saldo(guild_id, ctx.author.id)

        if cantidad > saldo:
            await ctx.send(
                f"No tienes suficientes fichas. Saldo: **{saldo}** 🪙\n"
                "Usa `/recargar` si te quedaste sin fichas.",
                ephemeral=True,
            )
            return

        msg = await ctx.send("🪙 Lanzando la moneda...")
        await asyncio.sleep(0.8)

        gano = random.random() < 0.5
        nuevo_saldo = self._ajustar(guild_id, ctx.author.id, cantidad if gano else -cantidad)

        if gano:
            embed = discord.Embed(
                title="🟡 ¡Cara! — ¡Ganaste! 🎉",
                description=f"+**{cantidad}** 🪙",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="⚫ Cruz — Perdiste",
                description=f"-**{cantidad}** 🪙",
                color=discord.Color.red(),
            )
        embed.add_field(name="Saldo", value=f"**{nuevo_saldo}** 🪙", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await msg.edit(content=None, embed=embed)

    @doble.error
    async def doble_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Espera {error.retry_after:.1f}s.", ephemeral=True)

    # ── /tragaperras ─────────────────────────────────────────────────────────

    @commands.hybrid_command(name="tragaperras", description="Tira de la palanca 🎰")
    @commands.guild_only()
    @app_commands.describe(cantidad="Fichas a apostar (default 100)")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tragaperras(self, ctx: commands.Context, cantidad: int = _APUESTA_DEFAULT):
        if cantidad < 1:
            await ctx.send("La apuesta mínima es **1** ficha.", ephemeral=True)
            return

        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self._saldo(guild_id, ctx.author.id)

        if cantidad > saldo:
            await ctx.send(
                f"No tienes suficientes fichas. Saldo: **{saldo}** 🪙\n"
                "Usa `/recargar` si te quedaste sin fichas.",
                ephemeral=True,
            )
            return

        msg = await ctx.send("🎰 Tirando de la palanca...")
        await asyncio.sleep(0.6)

        for _ in range(2):
            tmp = [random.choice(_SLOTS) for _ in range(3)]
            await msg.edit(content=f"[ {tmp[0]} | {tmp[1]} | {tmp[2]} ]  🎰")
            await asyncio.sleep(0.45)

        a, b, c = [random.choice(_SLOTS) for _ in range(3)]
        display = f"[ {a} | {b} | {c} ]"

        if a == b == c:
            mult = _SLOT_MULT[a]
            delta = cantidad * mult
            nuevo_saldo = self._ajustar(guild_id, ctx.author.id, delta)
            embed = discord.Embed(
                title=f"{display}  ¡JACKPOT! 🎉",
                description=f"+**{delta}** 🪙  (×{mult + 1})",
                color=0xFFD700,
            )
        elif a == b or c in (a, b):
            nuevo_saldo = self._ajustar(guild_id, ctx.author.id, 0)
            embed = discord.Embed(
                title=f"{display}  Par — Empate",
                description="Recuperas tu apuesta.",
                color=discord.Color.greyple(),
            )
        else:
            nuevo_saldo = self._ajustar(guild_id, ctx.author.id, -cantidad)
            embed = discord.Embed(
                title=f"{display}  Perdiste",
                description=f"-**{cantidad}** 🪙",
                color=discord.Color.red(),
            )

        embed.add_field(name="Saldo", value=f"**{nuevo_saldo}** 🪙", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await msg.edit(content=None, embed=embed)

    @tragaperras.error
    async def tragaperras_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Espera {error.retry_after:.1f}s.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Casino(bot))
