"""E2E: cog Games con HTTP mockeado para no pegar PokeAPI/OpenTDB."""

from io import BytesIO

import discord.ext.test as dpytest
import pytest
from aioresponses import aioresponses
from PIL import Image

pytestmark = pytest.mark.asyncio


def _png_bytes(size=(96, 96)) -> bytes:
    """PNG con transparencia parcial para que la silueta tenga forma."""
    img = Image.new("RGBA", size, (255, 0, 0, 255))
    for x in range(size[0] // 2):
        for y in range(size[1] // 2):
            img.putpixel((x, y), (0, 0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


POKEMON_FAKE = {
    "id": 25,
    "name": "pikachu",
    "sprites": {
        "front_default": "https://sprite.test/25.png",
        "other": {"official-artwork": {"front_default": "https://artwork.test/25.png"}},
    },
    "types": [{"type": {"name": "electric"}}],
}

SPECIES_FAKE = {
    "names": [
        {"language": {"name": "es"}, "name": "Pikachu"},
        {"language": {"name": "en"}, "name": "Pikachu"},
        {"language": {"name": "fr"}, "name": "Pikachu"},
    ],
    "generation": {"name": "generation-i"},
}


async def test_adivina_silueta_y_acierto(bot):
    sprite_png = _png_bytes()
    with aioresponses() as mocked:
        # PokeAPI usa cualquier id 1..1025; mockeamos cualquier llamada que case el patrón.
        mocked.get(
            "https://pokeapi.co/api/v2/pokemon/25",
            payload=POKEMON_FAKE,
            repeat=True,
        )
        mocked.get(
            "https://pokeapi.co/api/v2/pokemon-species/25",
            payload=SPECIES_FAKE,
            repeat=True,
        )
        mocked.get(
            "https://sprite.test/25.png",
            body=sprite_png,
            headers={"Content-Type": "image/png"},
            repeat=True,
        )

        # Forzamos el id para no depender de random.
        import cogs.games as games_mod

        original = games_mod.random.randint
        games_mod.random.randint = lambda a, b: 25
        try:
            await dpytest.message("<adivina")
        finally:
            games_mod.random.randint = original

        # 1er mensaje: el embed con la silueta
        first = dpytest.get_message()
        assert first.embeds
        assert "Pokémon" in first.embeds[0].title

        # Usuario contesta
        await dpytest.message("Pikachu")
        # debería llegar el embed de acierto con el nombre
        reveal = dpytest.get_message()
        assert reveal.embeds
        assert "Pikachu" in reveal.embeds[0].title


async def test_pokeranking_vacio(bot):
    await dpytest.message("<pokeranking")
    msg = dpytest.get_message()
    assert "Todavía nadie" in msg.content
