"""Mini-juegos: adivina el Pokémon, trivia."""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import random
import unicodedata
from collections import defaultdict
from io import BytesIO
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands
from PIL import Image

from src.fichas import get_manager
from src.http import HttpMixin

log = logging.getLogger("discord.games")

POKEMON_REWARD = 25  # fichas por acertar un Pokémon

POKEAPI = "https://pokeapi.co/api/v2"
MAX_POKEMON_ID = 493  # Gen 1–4

_DATA_DIR = Path(os.getenv("BOT_DATA_DIR", "."))
_POKEMON_RANKING_FILE = _DATA_DIR / "pokemon_ranking.json"

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
    """Genera silueta usando el canal alpha del sprite. Vectorizado en C vía PIL."""
    imagen = Image.open(BytesIO(imagen_bytes)).convert("RGBA")
    alpha = imagen.split()[-1]
    silueta = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    negro = Image.new("RGBA", imagen.size, (0, 0, 0, 255))
    silueta.paste(negro, mask=alpha)
    buf = BytesIO()
    silueta.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _load_pokemon_ranking() -> dict:
    if _POKEMON_RANKING_FILE.exists():
        try:
            return json.loads(_POKEMON_RANKING_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("No se pudo leer %s, empezando vacío", _POKEMON_RANKING_FILE)
    return {}


def _save_pokemon_ranking(data: dict) -> None:
    try:
        _POKEMON_RANKING_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        log.error("No se pudo guardar pokemon_ranking.json", exc_info=True)


class Games(HttpMixin, commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # ranking[guild_id][user_id] = puntos — cargado desde disco
        self.ranking: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        # Caché en memoria de datos de pokémon ya consultados (1025 × ~5KB = ~5MB tope).
        self._pokemon_cache: dict[int, tuple[dict, dict, bytes]] = {}
        self._session: aiohttp.ClientSession | None = None
        # Cargar ranking desde disco
        self._load_ranking_from_disk()

    def _load_ranking_from_disk(self) -> None:
        """Carga el ranking de pokemon desde pokemon_ranking.json."""
        data = _load_pokemon_ranking()
        for guild_id_str, scores in data.items():
            guild_id = int(guild_id_str)
            for user_id_str, puntos in scores.items():
                user_id = int(user_id_str)
                self.ranking[guild_id][user_id] = puntos
        if data:
            log.info("Ranking de pokemon cargado desde disco: %d servidores", len(data))

    def _save_ranking_to_disk(self) -> None:
        """Guarda el ranking actual a pokemon_ranking.json."""
        data = {}
        for guild_id, scores in self.ranking.items():
            data[str(guild_id)] = {str(uid): pts for uid, pts in scores.items()}
        _save_pokemon_ranking(data)

    async def _fetch_pokemon(self, pokemon_id: int) -> tuple[dict, dict, bytes] | None:
        """Devuelve (pokemon, species, sprite_bytes). Cachea para no machacar PokeAPI."""
        if pokemon_id in self._pokemon_cache:
            return self._pokemon_cache[pokemon_id]

        s = await self._get_session()
        timeout = aiohttp.ClientTimeout(total=10)

        async def _json(url: str) -> dict:
            async with s.get(url, timeout=timeout) as r:
                return await r.json()

        try:
            pokemon, species = await asyncio.gather(
                _json(f"{POKEAPI}/pokemon/{pokemon_id}"),
                _json(f"{POKEAPI}/pokemon-species/{pokemon_id}"),
            )
        except (TimeoutError, aiohttp.ClientError):
            return None

        # Sprite pequeño (96x96) para procesar en Raspberry; el artwork grande
        # se usa solo como URL en el embed final (lo renderiza Discord).
        sprite_url = pokemon.get("sprites", {}).get("front_default")
        if not sprite_url:
            return None
        try:
            async with s.get(sprite_url, timeout=timeout) as r:
                sprite_bytes = await r.read()
        except (TimeoutError, aiohttp.ClientError):
            return None

        result = (pokemon, species, sprite_bytes)
        self._pokemon_cache[pokemon_id] = result
        return result

    @staticmethod
    def _artwork_url(pokemon: dict) -> str | None:
        return pokemon.get("sprites", {}).get("other", {}).get("official-artwork", {}).get(
            "front_default"
        ) or pokemon.get("sprites", {}).get("front_default")

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

    @commands.hybrid_command(
        name="adivina",
        description=f"Adivina el Pokémon de la silueta. Acertar da {POKEMON_REWARD} 🪙",
    )
    @commands.cooldown(1, 3, commands.BucketType.channel)
    async def adivina(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.defer()

        result = await self._fetch_pokemon(random.randint(1, MAX_POKEMON_ID))
        if not result:
            await ctx.send("No pude obtener el Pokémon ahora mismo.")
            return
        pokemon, species, sprite_bytes = result

        nombres_norm = self._nombres_aceptados(species)
        nombre_es = next(
            (n["name"] for n in species["names"] if n["language"]["name"] == "es"),
            pokemon["name"].capitalize(),
        )

        loop = asyncio.get_running_loop()
        silueta_bytes = await loop.run_in_executor(None, obtener_silueta, sprite_bytes)
        artwork_url = self._artwork_url(pokemon)

        embed = discord.Embed(
            title="¿Quién es este Pokémon?",
            description="Tienes **30 segundos**. La pista llega a los 15s.",
            color=0xFFCB05,
        )
        embed.set_image(url="attachment://silueta.png")
        embed.set_footer(text=self._generacion(species))
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
                self._save_ranking_to_disk()
                fichas = get_manager().ajustar(ctx.guild.id, msg.author.id, POKEMON_REWARD)
                reveal = discord.Embed(
                    title=f"✅ ¡{nombre_es}!",
                    description=(
                        f"{msg.author.mention} acertó. "
                        f"Lleva **{puntos}** puntos en este servidor. "
                        f"+{POKEMON_REWARD} 🪙 (saldo: {fichas} 🪙)"
                    ),
                    color=self._color_por_tipo(pokemon),
                )
                if artwork_url:
                    reveal.set_thumbnail(url=artwork_url)
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
        if artwork_url:
            reveal.set_thumbnail(url=artwork_url)
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
            session = await self._get_session()
            async with session.get(
                "https://opentdb.com/api.php?amount=1&type=multiple",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
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
