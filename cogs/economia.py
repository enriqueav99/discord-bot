"""Economía del servidor: trabajo, heist, tienda con roles y títulos."""

from __future__ import annotations

import asyncio
import contextlib
import random
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from src.fichas import get_manager

_APUESTA_DEFAULT = 100
_HEIST_DURACION = 60

_TRABAJOS = [
    ("minero", 60, 140),
    ("carpintero", 50, 120),
    ("pescador", 40, 100),
    ("cocinero", 70, 130),
    ("guardia", 80, 160),
    ("mercader", 90, 200),
    ("herrero", 75, 150),
    ("escriba", 55, 110),
    ("alquimista", 100, 250),
    ("bufón", 10, 400),
]
_TRABAJO_MSGS = [
    "Trabajaste como {trabajo} y ganaste **{fichas}** 🪙.",
    "Un día duro de {trabajo}. Cobras **{fichas}** 🪙.",
    "Tu jefe quedó satisfecho. **{fichas}** 🪙 como {trabajo}.",
    "Otro día, otra moneda. **{fichas}** 🪙 por ser {trabajo}.",
    "Jornada completa como {trabajo}. Sueldo: **{fichas}** 🪙.",
]


class Economia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.fm = get_manager()
        self._exp_check.start()

    def cog_unload(self):
        self._exp_check.cancel()

    # ── Task: expirar compras de tienda ───────────────────────────────────────

    @tasks.loop(minutes=30)
    async def _exp_check(self):
        now = datetime.now(UTC)
        for guild in self.bot.guilds:
            gk = str(guild.id)
            gs = self.fm.shop_data().get(gk)
            if not gs:
                continue
            compras = gs.get("compras", {})
            items = gs.get("items", {})
            changed = False
            for uid_str in list(compras.keys()):
                member = guild.get_member(int(uid_str))
                user_c = compras[uid_str]
                for iid in list(user_c.keys()):
                    expira_str = user_c[iid].get("expira")
                    if not expira_str:
                        continue
                    if datetime.fromisoformat(expira_str) <= now:
                        del user_c[iid]
                        changed = True
                        item = items.get(iid, {})
                        if item.get("tipo") == "rol" and member:
                            rol = guild.get_role(item.get("rol_id", 0))
                            if rol and rol in member.roles:
                                with contextlib.suppress(discord.HTTPException):
                                    await member.remove_roles(rol, reason="Compra expirada")
                if not user_c:
                    del compras[uid_str]
            if changed:
                self.fm.save_shop()

    @_exp_check.before_loop
    async def _before_exp_check(self):
        await self.bot.wait_until_ready()

    # ── /trabajo ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="trabajo", description="Trabaja y gana fichas 💼 (cada 8h)")
    @commands.guild_only()
    @commands.cooldown(1, 8 * 3600, commands.BucketType.member)
    async def trabajo(self, ctx: commands.Context):
        nombre, minimo, maximo = random.choice(_TRABAJOS)
        fichas = random.randint(minimo, maximo)
        guild_id = ctx.guild.id if ctx.guild else 0
        nuevo = self.fm.ajustar(guild_id, ctx.author.id, fichas)
        msg = random.choice(_TRABAJO_MSGS).format(trabajo=nombre, fichas=fichas)
        embed = discord.Embed(description=msg, color=0x2ECC71)
        embed.add_field(name="Saldo", value=f"**{nuevo}** 🪙", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await ctx.send(embed=embed)

    @trabajo.error
    async def trabajo_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            horas = int(error.retry_after // 3600)
            minutos = int((error.retry_after % 3600) // 60)
            tiempo = f"{horas}h {minutos}m" if horas else f"{minutos}m"
            await ctx.send(f"Ya trabajaste hoy. Vuelve en **{tiempo}**.", ephemeral=True)

    # ── /heist + /unirse ──────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="heist", description="Inicia un atraco grupal 🦹 (60s para unirse)"
    )
    @commands.guild_only()
    @app_commands.describe(cantidad="Fichas a apostar")
    async def heist(self, ctx: commands.Context, cantidad: int = _APUESTA_DEFAULT):
        if cantidad < 1:
            await ctx.send("La apuesta mínima es 1 ficha.", ephemeral=True)
            return
        guild_id = ctx.guild.id if ctx.guild else 0
        if guild_id in self.fm.heists:
            await ctx.send("Ya hay un atraco activo. Únete con `/unirse`.", ephemeral=True)
            return
        saldo = self.fm.saldo(guild_id, ctx.author.id)
        if cantidad > saldo:
            await ctx.send(f"No tienes suficientes fichas. Saldo: **{saldo}** 🪙", ephemeral=True)
            return
        self.fm.heists[guild_id] = {
            "participantes": {ctx.author.id: cantidad},
            "channel_id": ctx.channel.id,
        }
        embed = discord.Embed(
            title="🦹 ¡Atraco en marcha!",
            description=(
                f"**{ctx.author.display_name}** ha iniciado un atraco con **{cantidad}** 🪙.\n"
                f"Tienes **{_HEIST_DURACION}s** para unirte con `/unirse [cantidad]`."
            ),
            color=0xE67E22,
        )
        await ctx.send(embed=embed)
        asyncio.create_task(self._resolver_heist(guild_id, _HEIST_DURACION))

    async def _resolver_heist(self, guild_id: int, delay: int):
        await asyncio.sleep(delay)
        heist = self.fm.heists.pop(guild_id, None)
        if not heist:
            return
        channel = self.bot.get_channel(heist["channel_id"])
        participantes = heist["participantes"]
        gano = random.random() < 0.5
        lineas = []
        guild = self.bot.get_guild(guild_id)
        for uid, apuesta in participantes.items():
            member = guild.get_member(uid) if guild else None
            nombre = member.display_name if member else f"<{uid}>"
            delta = apuesta if gano else -apuesta
            self.fm.ajustar(guild_id, uid, delta)
            signo = "+" if gano else "-"
            lineas.append(f"{'✅' if gano else '❌'} **{nombre}** {signo}**{apuesta}** 🪙")
        if channel:
            embed = discord.Embed(
                title="🦹 Resultado del atraco",
                description="\n".join(lineas),
                color=discord.Color.green() if gano else discord.Color.red(),
            )
            embed.set_footer(text="¡Ganasteis!" if gano else "¡Os pillaron!")
            with contextlib.suppress(discord.HTTPException):
                await channel.send(embed=embed)

    @commands.hybrid_command(name="unirse", description="Únete al atraco activo 🦹")
    @commands.guild_only()
    @app_commands.describe(cantidad="Fichas a apostar (default 100)")
    async def unirse(self, ctx: commands.Context, cantidad: int = _APUESTA_DEFAULT):
        guild_id = ctx.guild.id if ctx.guild else 0
        if guild_id not in self.fm.heists:
            await ctx.send("No hay ningún atraco activo.", ephemeral=True)
            return
        heist = self.fm.heists[guild_id]
        if ctx.author.id in heist["participantes"]:
            await ctx.send("Ya estás en el atraco.", ephemeral=True)
            return
        if cantidad < 1:
            await ctx.send("La apuesta mínima es 1 ficha.", ephemeral=True)
            return
        saldo = self.fm.saldo(guild_id, ctx.author.id)
        if cantidad > saldo:
            await ctx.send(f"No tienes suficientes fichas. Saldo: **{saldo}** 🪙", ephemeral=True)
            return
        heist["participantes"][ctx.author.id] = cantidad
        await ctx.send(f"🦹 {ctx.author.mention} se une al atraco con **{cantidad}** 🪙.")

    # ── /tienda ───────────────────────────────────────────────────────────────

    @commands.hybrid_group(name="tienda", description="Tienda del servidor 🛒", fallback="ver")
    @commands.guild_only()
    async def tienda(self, ctx: commands.Context):
        guild_id = ctx.guild.id if ctx.guild else 0
        gs = self.fm.guild_shop(guild_id)
        items = gs.get("items", {})
        if not items:
            await ctx.send(
                "La tienda está vacía. Los admins pueden añadir artículos con "
                "`/tienda add_rol` o `/tienda add_titulo`."
            )
            return
        lines = []
        for iid, item in items.items():
            tipo_icon = "👑" if item["tipo"] == "titulo" else "🎭"
            if item["tipo"] == "rol":
                duracion = (
                    f" ({item['duracion_dias']}d)" if item.get("duracion_dias") else " (permanente)"
                )
            else:
                duracion = ""
            lines.append(
                f"`#{iid}` {tipo_icon} **{item['nombre']}** — **{item['precio']}** 🪙{duracion}"
            )
        embed = discord.Embed(title="🛒 Tienda", description="\n".join(lines), color=0x9B59B6)
        embed.set_footer(text="Usa /tienda comprar <id> para comprar")
        await ctx.send(embed=embed)

    @tienda.command(name="comprar", description="Comprar un artículo de la tienda")
    @app_commands.describe(id="ID del artículo (ver /tienda)")
    async def tienda_comprar(self, ctx: commands.Context, id: int):
        guild_id = ctx.guild.id if ctx.guild else 0
        gs = self.fm.guild_shop(guild_id)
        item = gs["items"].get(str(id))
        if not item:
            await ctx.send(f"Artículo `#{id}` no encontrado.", ephemeral=True)
            return
        uid_str = str(ctx.author.id)
        user_compras = gs["compras"].setdefault(uid_str, {})
        now = datetime.now(UTC)
        if str(id) in user_compras:
            c = user_compras[str(id)]
            expira = c.get("expira")
            if not expira or datetime.fromisoformat(expira) > now:
                await ctx.send("Ya tienes este artículo activo.", ephemeral=True)
                return
        saldo = self.fm.saldo(guild_id, ctx.author.id)
        if item["precio"] > saldo:
            await ctx.send(
                f"No tienes suficientes fichas. Necesitas **{item['precio']}** 🪙, "
                f"tienes **{saldo}** 🪙.",
                ephemeral=True,
            )
            return
        nuevo = self.fm.ajustar(guild_id, ctx.author.id, -item["precio"])
        expira_str = None
        if item.get("duracion_dias"):
            expira_str = (now + timedelta(days=item["duracion_dias"])).isoformat()
        user_compras[str(id)] = {"expira": expira_str}
        self.fm.save_shop()
        if item["tipo"] == "rol" and ctx.guild:
            rol = ctx.guild.get_role(item["rol_id"])
            if rol:
                with contextlib.suppress(discord.HTTPException):
                    await ctx.author.add_roles(rol, reason="Compra en tienda")
        duracion_txt = (
            f" durante **{item['duracion_dias']}** días"
            if item.get("duracion_dias")
            else " permanentemente"
        )
        await ctx.send(f"✅ Compraste **{item['nombre']}**{duracion_txt}. Saldo: **{nuevo}** 🪙")

    @tienda.command(name="add_rol", description="[Admin] Añadir artículo de rol a la tienda")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        rol="Rol de Discord a vender",
        precio="Precio en fichas",
        duracion_dias="Duración en días (0 = permanente)",
    )
    async def tienda_add_rol(
        self,
        ctx: commands.Context,
        rol: discord.Role,
        precio: int,
        duracion_dias: int = 0,
    ):
        if precio < 1:
            await ctx.send("El precio debe ser al menos 1.", ephemeral=True)
            return
        guild_id = ctx.guild.id if ctx.guild else 0
        gs = self.fm.guild_shop(guild_id)
        iid = str(gs["next_id"])
        gs["next_id"] += 1
        gs["items"][iid] = {
            "nombre": rol.name,
            "tipo": "rol",
            "rol_id": rol.id,
            "precio": precio,
            "duracion_dias": duracion_dias if duracion_dias > 0 else None,
        }
        self.fm.save_shop()
        duracion_txt = f"{duracion_dias} días" if duracion_dias > 0 else "permanente"
        await ctx.send(f"✅ Añadido `#{iid}` **{rol.name}** — {precio} 🪙 ({duracion_txt})")

    @tienda.command(name="add_titulo", description="[Admin] Añadir título cosmético a la tienda")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        titulo="Texto del título cosmético",
        precio="Precio en fichas",
        duracion_dias="Duración en días (0 = permanente)",
    )
    async def tienda_add_titulo(
        self,
        ctx: commands.Context,
        titulo: str,
        precio: int,
        duracion_dias: int = 0,
    ):
        if precio < 1:
            await ctx.send("El precio debe ser al menos 1.", ephemeral=True)
            return
        guild_id = ctx.guild.id if ctx.guild else 0
        gs = self.fm.guild_shop(guild_id)
        iid = str(gs["next_id"])
        gs["next_id"] += 1
        gs["items"][iid] = {
            "nombre": titulo,
            "tipo": "titulo",
            "titulo": titulo,
            "precio": precio,
            "duracion_dias": duracion_dias if duracion_dias > 0 else None,
        }
        self.fm.save_shop()
        duracion_txt = f"{duracion_dias} días" if duracion_dias > 0 else "permanente"
        await ctx.send(f"✅ Añadido `#{iid}` título **{titulo}** — {precio} 🪙 ({duracion_txt})")

    @tienda.command(name="remove", description="[Admin] Eliminar artículo de la tienda")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(id="ID del artículo a eliminar")
    async def tienda_remove(self, ctx: commands.Context, id: int):
        guild_id = ctx.guild.id if ctx.guild else 0
        gs = self.fm.guild_shop(guild_id)
        if str(id) not in gs["items"]:
            await ctx.send(f"Artículo `#{id}` no encontrado.", ephemeral=True)
            return
        nombre = gs["items"].pop(str(id))["nombre"]
        self.fm.save_shop()
        await ctx.send(f"✅ Eliminado `#{id}` **{nombre}**.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Economia(bot))
