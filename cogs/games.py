"""Mini-juegos: adivina el Pokémon, trivia."""

from __future__ import annotations

import asyncio
import html
import random
import unicodedata
from collections import defaultdict
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands
from PIL import Image

POKEAPI = "https://pokeapi.co/api/v2"
MAX_POKEMON_ID = 1025  # Gen 1–9

TYPE_COLORS = {
    "normal": 0xA8A77A,
    "fire": 0xEE8130,
    "water": 0x6390F0,
    "electric": 0xF7D02C,
    "grass": 0x7AC74C,
    "ice": 0x96D9D6,
    "fighting": 0xC22E28,
    "poison": 0xA33EA1,
    "ground": 0xE2BF65,
    "flying": 0xA98FF3,
    "psychic": 0xF95587,
    "bug": 0xA6B91A,
    "rock": 0xB6A136,
    "ghost": 0x735797,
    "dragon": 0x6F35FC,
    "dark": 0x705746,
    "steel": 0xB7B7CE,
    "fairy": 0xD685AD,
}


def normalizar(texto: str) -> str:
    """Lowercase + sin acentos + sin espacios para matching laxo."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return (
        "".join(c for c in nfkd if not unicodedata.combining(c)).replace(" ", "").replace("-", "")
    )


def obtener_silueta(imagen_bytes: bytes) -> bytes:
    imagen = Image.open(BytesIO(imagen_bytes)).convert("RGBA")
    out = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    pixels = imagen.load()
    salida = out.load()
    for y in range(imagen.size[1]):
        for x in range(imagen.size[0]):
            r, g, b, a = pixels[x, y]
            if a > 0:
                salida[x, y] = (0, 0, 0, 255)
    buf = BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # ranking[guild_id][user_id] = puntos
        self.ranking: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    async def _fetch_pokemon(self, pokemon_id: int) -> tuple[dict, dict] | None:
        async with aiohttp.ClientSession() as s:
            try:
                async with s.get(f"{POKEAPI}/pokemon/{pokemon_id}", timeout=10) as r:
                    pokemon = await r.json()
                async with s.get(f"{POKEAPI}/pokemon-species/{pokemon_id}", timeout=10) as r:
                    species = await r.json()
            except (TimeoutError, aiohttp.ClientError):
                return None
        return pokemon, species

    @staticmethod
    def _nombres_aceptados(species: dict) -> list[str]:
        """Devuelve nombres válidos en varios idiomas (es, en) normalizados."""
        idiomas_aceptados = {"es", "en"}
        return [
            normalizar(n["name"])
            for n in species.get("names", [])
            if n["language"]["name"] in idiomas_aceptados
        ]

    @staticmethod
    def _color_por_tipo(pokemon: dict) -> int:
        types = pokemon.get("types", [])
        if not types:
            return 0xCCCCCC
        return TYPE_COLORS.get(types[0]["type"]["name"], 0xCCCCCC)

    @staticmethod
    def _generacion(species: dict) -> str:
        gen_url = species.get("generation", {}).get("name", "")
        return gen_url.replace("generation-", "Gen ").upper() or "?"

    @commands.hybrid_command(name="adivina", description="Adivina el Pokémon de la silueta")
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def adivina(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer()

        result = await self._fetch_pokemon(random.randint(1, MAX_POKEMON_ID))
        if not result:
            await ctx.send("No pude obtener el Pokémon ahora mismo.")
            return
        pokemon, species = result

        sprite_url = pokemon.get("sprites", {}).get("other", {}).get("official-artwork", {}).get(
            "front_default"
        ) or pokemon.get("sprites", {}).get("front_default")
        if not sprite_url:
            await ctx.send("Este Pokémon no tiene sprite. Reintenta.")
            return

        try:
            async with aiohttp.ClientSession() as s, s.get(sprite_url, timeout=10) as r:
                img_bytes = await r.read()
        except (TimeoutError, aiohttp.ClientError):
            await ctx.send("Error descargando la imagen.")
            return

        nombres_norm = self._nombres_aceptados(species)
        nombre_es = next(
            (n["name"] for n in species["names"] if n["language"]["name"] == "es"),
            pokemon["name"].capitalize(),
        )

        loop = asyncio.get_running_loop()
        silueta_bytes = await loop.run_in_executor(None, obtener_silueta, img_bytes)

        embed = discord.Embed(
            title="¿Quién es este Pokémon?",
            description="Tienes **30 segundos**. La pista llega a los 15s.",
            color=0xFFCB05,
        )
        embed.set_image(url="attachment://silueta.png")
        embed.set_footer(text=f"{self._generacion(species)} • Pokémon #{pokemon['id']}")
        await ctx.send(
            embed=embed, file=discord.File(BytesIO(silueta_bytes), filename="silueta.png")
        )

        def check(msg: discord.Message) -> bool:
            return msg.channel == ctx.channel and not msg.author.bot

        end_time = asyncio.get_running_loop().time() + 30
        pista_dada = False

        while True:
            remaining = end_time - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            try:
                if not pista_dada and remaining <= 15:
                    await ctx.send(
                        f"💡 Pista: empieza por **{nombre_es[0].upper()}** "
                        f"y tiene **{len(nombre_es)}** letras."
                    )
                    pista_dada = True
                msg = await self.bot.wait_for("message", check=check, timeout=remaining)
            except TimeoutError:
                break
            if normalizar(msg.content) in nombres_norm:
                self.ranking[ctx.guild.id][msg.author.id] += 1
                puntos = self.ranking[ctx.guild.id][msg.author.id]
                reveal = discord.Embed(
                    title=f"✅ ¡{nombre_es}!",
                    description=f"{msg.author.mention} acertó. Lleva **{puntos}** puntos en este servidor.",
                    color=self._color_por_tipo(pokemon),
                )
                reveal.set_thumbnail(url=sprite_url)
                tipos = ", ".join(t["type"]["name"] for t in pokemon.get("types", []))
                if tipos:
                    reveal.add_field(name="Tipo(s)", value=tipos, inline=True)
                reveal.add_field(name="Nº Pokédex", value=pokemon["id"], inline=True)
                await ctx.send(embed=reveal)
                return

        # Timeout
        reveal = discord.Embed(
            title=f"⏱️ Se acabó el tiempo. Era **{nombre_es}**.",
            color=self._color_por_tipo(pokemon),
        )
        reveal.set_thumbnail(url=sprite_url)
        await ctx.send(embed=reveal)

    @adivina.error
    async def adivina_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"Espera {error.retry_after:.1f}s antes de volver a usar el comando.",
                ephemeral=True,
            )

    @commands.hybrid_command(name="pokeranking", description="Top de aciertos en /adivina")
    async def pokeranking(self, ctx: commands.Context):
        scores = self.ranking.get(ctx.guild.id) if ctx.guild else None
        if not scores:
            await ctx.send("Todavía nadie ha acertado. ¡A jugar!")
            return
        top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:10]
        lineas = []
        medallas = ["🥇", "🥈", "🥉"]
        for i, (uid, pts) in enumerate(top):
            user = ctx.guild.get_member(uid)
            nombre = user.display_name if user else f"<usuario {uid}>"
            prefijo = medallas[i] if i < 3 else f"`{i + 1}.`"
            lineas.append(f"{prefijo} **{nombre}** — {pts} pts")
        embed = discord.Embed(
            title="🏆 Top adivinadores Pokémon",
            description="\n".join(lineas),
            color=0xFFCB05,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="trivia", description="Pregunta de trivia simple")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def trivia(self, ctx: commands.Context):
        try:
            async with (
                aiohttp.ClientSession() as s,
                s.get("https://opentdb.com/api.php?amount=1&type=multiple", timeout=10) as resp,
            ):
                data = await resp.json()
        except (TimeoutError, aiohttp.ClientError):
            await ctx.send("La API de trivia no responde.")
            return

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
