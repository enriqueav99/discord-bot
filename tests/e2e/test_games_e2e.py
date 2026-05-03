"""E2E: cog Games con HTTP mockeado para no pegar PokeAPI."""

from io import BytesIO

import pytest
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
    ],
    "generation": {"name": "generation-i"},
}


async def test_adivina_acierto(harness, monkeypatch):
    """Pre-pobla la cache de pokémon para evitar HTTP, parchea wait_for para
    simular que el usuario contesta correctamente, y verifica que el bot
    responde con el embed de acierto.
    """
    sprite_png = _png_bytes()
    import cogs.games as games_mod

    monkeypatch.setattr(games_mod, "is_whitelisted", lambda uid: True)
    monkeypatch.setattr(games_mod.random, "randint", lambda a, b: 25)

    games = harness.bot.get_cog("Games")
    games._pokemon_cache[25] = (POKEMON_FAKE, SPECIES_FAKE, sprite_png)

    cmd = harness.bot.get_command("adivina")
    ctx = harness._make_ctx()

    captured = {"author": ctx.author, "channel": ctx.channel}

    async def mock_wait_for(event, *, check, timeout):
        m = type("M", (), {})()
        m.author = captured["author"]
        m.author.bot = False
        m.channel = captured["channel"]
        m.content = "Pikachu"
        return m

    harness.bot.wait_for = mock_wait_for

    await cmd.callback(cmd.cog, ctx)

    assert ctx.send.await_count >= 2
    embeds = [c.kwargs.get("embed") for c in ctx.send.call_args_list if c.kwargs.get("embed")]
    assert any("Pikachu" in (e.title or "") for e in embeds)


async def test_pokeranking_vacio(harness):
    result = await harness.invoke("pokeranking")
    assert "Todavía nadie" in result.all_text


async def test_pokeranking_con_aciertos(harness):
    games = harness.bot.get_cog("Games")
    games.ranking[100][111] = 5
    games.ranking[100][222] = 3

    result = await harness.invoke("pokeranking")
    assert result.embeds
    assert "5 pts" in result.all_text
    assert "3 pts" in result.all_text
