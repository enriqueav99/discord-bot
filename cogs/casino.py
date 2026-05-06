"""Juegos de casino: ruleta, blackjack, tragaperras, doble. Fichas y ranking."""

from __future__ import annotations

import asyncio
import contextlib
import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from src.fichas import get_manager

_APUESTA_DEFAULT = 100
_RECARGA = 500
_COOLDOWN_RECARGA_H = 6
_MAX_APUESTAS = 8

_ROJOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

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

# Blackjack
_BJ_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
_BJ_SUITS = ["♠", "♥", "♦", "♣"]


# ── Ruleta helpers ────────────────────────────────────────────────────────────


def _color_emoji(n: int) -> str:
    if n == 0:
        return "🟢"
    return "🔴" if n in _ROJOS else "⚫"


def _wheel_display(numero: int) -> str:
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
    """Parse 'bet1 [amount1] bet2 [amount2] …' de una sola cadena.

    Un entero ≥ 1 tras un token de apuesta se consume como cantidad de esa apuesta.
    Devuelve (apuestas_válidas, tokens_inválidos).
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
                    if pending not in seen:
                        seen.add(pending)
                        valid.append((pending[0], pending[1], n))
                    pending = None
                    continue
                # n == 0: fall through → "0" es apuesta al número 0
            except ValueError:
                pass
        result = _parse_apuesta(token)
        if result is not None:
            if pending is not None and pending not in seen:
                seen.add(pending)
                valid.append((pending[0], pending[1], default_cantidad))
            pending = result
        else:
            invalid.append(token)

    if pending is not None and pending not in seen:
        seen.add(pending)
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


# ── Blackjack helpers ─────────────────────────────────────────────────────────


def _bj_carta() -> str:
    return f"{random.choice(_BJ_RANKS)}{random.choice(_BJ_SUITS)}"


def _bj_valor(mano: list[str]) -> int:
    total, ases = 0, 0
    for c in mano:
        rank = c[:-1]
        if rank == "A":
            total += 11
            ases += 1
        elif rank in ("J", "Q", "K"):
            total += 10
        else:
            total += int(rank)
    while total > 21 and ases:
        total -= 10
        ases -= 1
    return total


def _bj_mano_str(mano: list[str], ocultar_segunda: bool = False) -> str:
    if ocultar_segunda and len(mano) >= 2:
        return f"`{mano[0]}`  `🂠`"
    return "  ".join(f"`{c}`" for c in mano)


class _BlackjackView(discord.ui.View):
    def __init__(
        self,
        jugador: list[str],
        dealer: list[str],
        cantidad: int,
        guild_id: int,
        user_id: int,
        cog: Casino,
    ):
        super().__init__(timeout=60)
        self.jugador = jugador
        self.dealer = dealer
        self.cantidad = cantidad
        self.guild_id = guild_id
        self.user_id = user_id
        self.cog = cog
        self.message: discord.Message | None = None

    def _embed_juego(self) -> discord.Embed:
        pj = _bj_valor(self.jugador)
        embed = discord.Embed(title="🃏 Blackjack", color=0x2C3E50)
        embed.add_field(name=f"Tu mano ({pj})", value=_bj_mano_str(self.jugador), inline=False)
        embed.add_field(
            name="Dealer", value=_bj_mano_str(self.dealer, ocultar_segunda=True), inline=False
        )
        embed.set_footer(text=f"Apuesta: {self.cantidad} 🪙  •  Pedir carta o plantarse")
        return embed

    def _embed_final(self, resultado: str, nuevo_saldo: int) -> discord.Embed:
        pj = _bj_valor(self.jugador)
        pd = _bj_valor(self.dealer)
        match resultado:
            case "bj":
                title, color = "🃏 ¡Blackjack! 🎉", discord.Color.gold()
            case "bust":
                title, color = f"💥 ¡Te pasaste! ({pj}) — Perdiste", discord.Color.red()
            case "win":
                title, color = f"🏆 ¡Ganaste! ({pj} vs {pd}) 🎉", discord.Color.green()
            case "tie":
                title, color = f"🤝 Empate ({pj})", discord.Color.greyple()
            case _:
                title, color = f"😔 Perdiste ({pj} vs {pd})", discord.Color.red()
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name=f"Tu mano ({pj})", value=_bj_mano_str(self.jugador), inline=True)
        embed.add_field(name=f"Dealer ({pd})", value=_bj_mano_str(self.dealer), inline=True)
        embed.add_field(name="Saldo", value=f"**{nuevo_saldo}** 🪙", inline=False)
        embed.set_footer(text=f"Apuesta: {self.cantidad} 🪙")
        return embed

    async def _terminar(self, interaction: discord.Interaction, resultado: str, delta: int):
        nuevo_saldo = self.cog.fm.ajustar(self.guild_id, self.user_id, delta)
        await interaction.response.edit_message(
            embed=self._embed_final(resultado, nuevo_saldo), view=None
        )
        self.stop()

    async def _plantarse_interno(self, interaction: discord.Interaction):
        while _bj_valor(self.dealer) < 17:
            self.dealer.append(_bj_carta())
        pj, pd = _bj_valor(self.jugador), _bj_valor(self.dealer)
        if pd > 21 or pj > pd:
            await self._terminar(interaction, "win", self.cantidad)
        elif pj == pd:
            await self._terminar(interaction, "tie", 0)
        else:
            await self._terminar(interaction, "lose", -self.cantidad)

    @discord.ui.button(label="Pedir carta", style=discord.ButtonStyle.primary, emoji="🃏")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.jugador.append(_bj_carta())
        total = _bj_valor(self.jugador)
        if total > 21:
            await self._terminar(interaction, "bust", -self.cantidad)
        elif total == 21:
            await self._plantarse_interno(interaction)
        else:
            await interaction.response.edit_message(embed=self._embed_juego())

    @discord.ui.button(label="Plantarse", style=discord.ButtonStyle.secondary, emoji="✋")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._plantarse_interno(interaction)

    async def on_timeout(self):
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=None)


# ── Cog ───────────────────────────────────────────────────────────────────────


class Casino(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.fm = get_manager()

    # ── /ruleta ───────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="ruleta", description="Apuesta en la ruleta del casino 🎰")
    @commands.guild_only()
    @app_commands.describe(
        apuestas="apuesta [cantidad] … ej: 'negro 50 alto 30 0 20' o 'rojo negro par'",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ruleta(self, ctx: commands.Context, *, apuestas: str):
        validas, invalidas = _parse_apuestas(apuestas, _APUESTA_DEFAULT)

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
        saldo = self.fm.saldo(guild_id, ctx.author.id)
        coste_total = sum(bet[2] for bet in validas)

        if coste_total > saldo:
            desglose = " + ".join(str(bet[2]) for bet in validas)
            await ctx.send(
                f"No tienes suficientes fichas. Necesitas **{coste_total}** 🪙 "
                f"({desglose}), saldo: **{saldo}** 🪙\nUsa `/recargar` si te quedaste sin fichas.",
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

        nuevo_saldo = self.fm.ajustar(guild_id, ctx.author.id, delta_total)

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

    # ── /fichas ───────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="fichas", description="Consulta tu saldo de fichas 🪙")
    @commands.guild_only()
    async def fichas_cmd(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self.fm.saldo(guild_id, ctx.author.id)
        await ctx.send(f"{ctx.author.mention} tiene **{saldo}** fichas 🪙")

    # ── /recargar ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="recargar",
        description=f"Recibe {_RECARGA} fichas gratis (cada {_COOLDOWN_RECARGA_H}h) 🎁",
    )
    @commands.guild_only()
    @commands.cooldown(1, _COOLDOWN_RECARGA_H * 3600, commands.BucketType.member)
    async def recargar(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        nuevo = self.fm.ajustar(guild_id, ctx.author.id, _RECARGA)
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

    # ── /ranking_fichas ───────────────────────────────────────────────────────

    @commands.hybrid_command(name="ranking_fichas", description="Top de fichas en el servidor 🏆")
    @commands.guild_only()
    async def ranking_fichas(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        scores = self.fm.todos(guild_id)
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
            titulo = self.fm.active_title(guild_id, int(uid_str))
            titulo_str = f" *{titulo}*" if titulo else ""
            lineas.append(f"{prefijo} **{nombre}**{titulo_str} — {saldo} 🪙")
        embed = discord.Embed(
            title="🏆 Ranking de fichas",
            description="\n".join(lineas),
            color=0xFFD700,
        )
        await ctx.send(embed=embed)

    # ── /doble ────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="doble", description="Cara o cruz: dobla o pierde tus fichas 🪙")
    @commands.guild_only()
    @app_commands.describe(cantidad="Fichas a apostar (default 100)")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def doble(self, ctx: commands.Context, cantidad: int = _APUESTA_DEFAULT):
        if cantidad < 1:
            await ctx.send("La apuesta mínima es **1** ficha.", ephemeral=True)
            return
        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self.fm.saldo(guild_id, ctx.author.id)
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
        nuevo_saldo = self.fm.ajustar(guild_id, ctx.author.id, cantidad if gano else -cantidad)

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

    # ── /tragaperras ──────────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="tragaperras", description="Tira de la palanca — cuadrícula 3×3 🎰"
    )
    @commands.guild_only()
    @app_commands.describe(cantidad="Fichas a apostar (default 100)")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tragaperras(self, ctx: commands.Context, cantidad: int = _APUESTA_DEFAULT):
        if cantidad < 1:
            await ctx.send("La apuesta mínima es **1** ficha.", ephemeral=True)
            return
        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self.fm.saldo(guild_id, ctx.author.id)
        if cantidad > saldo:
            await ctx.send(
                f"No tienes suficientes fichas. Saldo: **{saldo}** 🪙\n"
                "Usa `/recargar` si te quedaste sin fichas.",
                ephemeral=True,
            )
            return

        def _grid(rows: list[list[str]], mark_mid: bool = False) -> str:
            lines = []
            for i, row in enumerate(rows):
                line = f"[ {' | '.join(row)} ]"
                if mark_mid and i == 1:
                    line += "  ◀"
                lines.append(line)
            return "\n".join(lines)

        msg = await ctx.send("🎰 Tirando de la palanca...")
        await asyncio.sleep(0.5)
        for _ in range(2):
            tmp = [[random.choice(_SLOTS) for _ in range(3)] for _ in range(3)]
            await msg.edit(content=_grid(tmp))
            await asyncio.sleep(0.4)

        grid = [[random.choice(_SLOTS) for _ in range(3)] for _ in range(3)]
        a, b, c = grid[1]  # fila central determina el resultado

        if a == b == c:
            mult = _SLOT_MULT[a]
            delta = cantidad * mult
            nuevo_saldo = self.fm.ajustar(guild_id, ctx.author.id, delta)
            embed = discord.Embed(
                title="¡JACKPOT! 🎉",
                description=f"{_grid(grid, mark_mid=True)}\n\n+**{delta}** 🪙  (×{mult + 1})",
                color=0xFFD700,
            )
        elif a == b or c in (a, b):
            nuevo_saldo = self.fm.ajustar(guild_id, ctx.author.id, 0)
            embed = discord.Embed(
                title="Par — Empate",
                description=f"{_grid(grid, mark_mid=True)}\n\nRecuperas tu apuesta.",
                color=discord.Color.greyple(),
            )
        else:
            nuevo_saldo = self.fm.ajustar(guild_id, ctx.author.id, -cantidad)
            embed = discord.Embed(
                title="Perdiste",
                description=f"{_grid(grid, mark_mid=True)}\n\n-**{cantidad}** 🪙",
                color=discord.Color.red(),
            )

        embed.add_field(name="Saldo", value=f"**{nuevo_saldo}** 🪙", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await msg.edit(content=None, embed=embed)

    @tragaperras.error
    async def tragaperras_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Espera {error.retry_after:.1f}s.", ephemeral=True)

    # ── /blackjack ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="blackjack", description="Juega al blackjack contra la banca 🃏")
    @commands.guild_only()
    @app_commands.describe(cantidad="Fichas a apostar (default 100)")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context, cantidad: int = _APUESTA_DEFAULT):
        if cantidad < 1:
            await ctx.send("La apuesta mínima es **1** ficha.", ephemeral=True)
            return
        guild_id = ctx.guild.id if ctx.guild else 0
        saldo = self.fm.saldo(guild_id, ctx.author.id)
        if cantidad > saldo:
            await ctx.send(
                f"No tienes suficientes fichas. Saldo: **{saldo}** 🪙\n"
                "Usa `/recargar` si te quedaste sin fichas.",
                ephemeral=True,
            )
            return

        jugador = [_bj_carta(), _bj_carta()]
        dealer = [_bj_carta(), _bj_carta()]

        if _bj_valor(jugador) == 21:
            delta = int(cantidad * 1.5)
            nuevo_saldo = self.fm.ajustar(guild_id, ctx.author.id, delta)
            embed = discord.Embed(title="🃏 ¡Blackjack Natural! 🎉", color=discord.Color.gold())
            embed.add_field(name="Tu mano (21)", value=_bj_mano_str(jugador), inline=True)
            embed.add_field(
                name=f"Dealer ({_bj_valor(dealer)})", value=_bj_mano_str(dealer), inline=True
            )
            embed.add_field(name="Ganancia", value=f"+**{delta}** 🪙 (×2.5)", inline=False)
            embed.add_field(name="Saldo", value=f"**{nuevo_saldo}** 🪙", inline=True)
            await ctx.send(embed=embed)
            return

        view = _BlackjackView(jugador, dealer, cantidad, guild_id, ctx.author.id, self)
        view.message = await ctx.send(embed=view._embed_juego(), view=view)

    @blackjack.error
    async def blackjack_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Espera {error.retry_after:.1f}s.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Casino(bot))
