"""Mini-juegos."""

from __future__ import annotations

import asyncio
import random

import aiohttp
import discord
from discord.ext import commands
from PIL import Image


def obtener_silueta(imagen_path: str) -> Image.Image:
    imagen = Image.open(imagen_path)
    imagen_gris = imagen.convert("L")
    umbral = 100
    silueta = imagen_gris.point(lambda p: 0 if p < umbral else 255)
    final = Image.new("RGB", imagen.size, "black")
    final.paste(silueta, (0, 0), silueta)
    return final


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="adivina", description="Adivina el Pokémon de la silueta")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def adivina(self, ctx: commands.Context):
        await ctx.defer() if ctx.interaction else None
        pokemon_id = random.randint(1, 898)
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=10) as resp:
                    data = await resp.json()
                async with s.get(data["sprites"]["front_default"], timeout=10) as resp:
                    img_bytes = await resp.read()
        except (TimeoutError, aiohttp.ClientError, KeyError):
            await ctx.send("No pude obtener el Pokémon ahora mismo.")
            return

        nombre = data["name"].capitalize()
        loop = asyncio.get_running_loop()

        def _process():
            with open("img/pokemon_temp.png", "wb") as f:
                f.write(img_bytes)
            silueta = obtener_silueta("img/pokemon_temp.png")
            silueta.save("img/silueta_pokemon.png")

        await loop.run_in_executor(None, _process)

        await ctx.send("Adivina este Pokémon, tienes 30 segundos!")
        with open("img/silueta_pokemon.png", "rb") as f:
            await ctx.send(file=discord.File(f, filename="silueta.png"))

        def check(msg: discord.Message):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            response = await self.bot.wait_for("message", check=check, timeout=30)
            if response.content.lower() == nombre.lower():
                await ctx.send(f"¡Correcto, {ctx.author.mention}! Era **{nombre}**.")
            else:
                await ctx.send(f"¡Incorrecto! Era **{nombre}**.")
        except TimeoutError:
            await ctx.send(f"Se acabó el tiempo. El Pokémon era **{nombre}**.")

    @adivina.error
    async def adivina_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"Espera {error.retry_after:.1f}s antes de volver a usar el comando.",
                ephemeral=True,
            )

    @commands.hybrid_command(name="trivia", description="Pregunta de trivia simple")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def trivia(self, ctx: commands.Context):
        try:
            async with (
                aiohttp.ClientSession() as s,
                s.get(
                    "https://opentdb.com/api.php?amount=1&type=multiple",
                    timeout=10,
                ) as resp,
            ):
                data = await resp.json()
        except (TimeoutError, aiohttp.ClientError):
            await ctx.send("La API de trivia no responde.")
            return

        import html

        pregunta_data = data["results"][0]
        question = html.unescape(pregunta_data["question"])
        correct = html.unescape(pregunta_data["correct_answer"])
        opciones = [html.unescape(o) for o in pregunta_data["incorrect_answers"]]
        opciones.append(correct)
        random.shuffle(opciones)

        letras = ["A", "B", "C", "D"]
        texto = "\n".join(f"**{letras[i]}.** {o}" for i, o in enumerate(opciones))
        await ctx.send(f"❓ {question}\n\n{texto}\n\n*Tienes 20s.*")

        def check(m: discord.Message):
            return (
                m.author == ctx.author and m.channel == ctx.channel and m.content.upper() in letras
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=20)
            elegida = opciones[letras.index(msg.content.upper())]
            if elegida == correct:
                await ctx.send(f"✅ ¡Correcto, {ctx.author.mention}!")
            else:
                await ctx.send(f"❌ Era: **{correct}**")
        except TimeoutError:
            await ctx.send(f"⏱️ Se acabó el tiempo. Era: **{correct}**")


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
