"""E2E: comandos generales."""

import discord.ext.test as dpytest
import pytest

pytestmark = pytest.mark.asyncio


async def test_ping(bot):
    await dpytest.message("<ping")
    msg = dpytest.get_message()
    assert "pong" in msg.content.lower()


async def test_saludar(bot):
    await dpytest.message("<saludar")
    msg = dpytest.get_message()
    assert "Hola" in msg.content


async def test_info_envia_embed(bot):
    await dpytest.message("<info")
    msg = dpytest.get_message()
    assert msg.embeds, "info debería responder con un embed"
    assert "Bot de Korea" in msg.embeds[0].title


async def test_help_korea_lista_categorias(bot):
    await dpytest.message("<help_korea")
    msg = dpytest.get_message()
    assert msg.embeds
    fields = {f.name for f in msg.embeds[0].fields}
    assert {"General", "Música", "Juegos", "Moderación"} <= fields


async def test_comando_inexistente_no_revienta(bot):
    await dpytest.message("<no_existe")
    assert dpytest.sent_queue.empty()
