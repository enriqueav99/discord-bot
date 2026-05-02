"""E2E: comandos generales."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_ping(harness):
    result = await harness.invoke("ping")
    assert "pong" in result.all_text.lower()


async def test_saludar(harness):
    result = await harness.invoke("saludar")
    assert "Hola" in result.all_text


async def test_info_envia_embed(harness):
    result = await harness.invoke("info")
    assert result.embeds, "info debería responder con un embed"
    assert "Bot de Korea" in result.embeds[0].title


async def test_help_korea_lista_categorias(harness):
    result = await harness.invoke("help_korea")
    assert result.embeds
    field_names = {f.name for f in result.embeds[0].fields}
    assert {"General", "Música", "Juegos", "Moderación"} <= field_names
