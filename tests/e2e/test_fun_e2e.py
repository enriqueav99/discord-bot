"""E2E: cog Fun."""

import discord.ext.test as dpytest
import pytest

pytestmark = pytest.mark.asyncio


async def test_8ball(bot):
    await dpytest.message("<8ball ¿gana hoy el madrid?")
    msg = dpytest.get_message()
    assert "🎱" in msg.content


async def test_dado_default(bot):
    await dpytest.message("<dado")
    msg = dpytest.get_message()
    assert "🎲" in msg.content


async def test_dado_caras_invalidas(bot):
    await dpytest.message("<dado 1")
    msg = dpytest.get_message()
    assert "entre 2 y 1000" in msg.content


async def test_moneda(bot):
    await dpytest.message("<moneda")
    msg = dpytest.get_message()
    assert "Cara" in msg.content or "Cruz" in msg.content


async def test_choose_pocas_opciones(bot):
    await dpytest.message("<choose solo_una")
    msg = dpytest.get_message()
    assert "al menos 2" in msg.content


async def test_choose_funciona(bot):
    await dpytest.message("<choose pizza | pasta | sushi")
    msg = dpytest.get_message()
    assert any(opt in msg.content for opt in ["pizza", "pasta", "sushi"])
