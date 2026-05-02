"""E2E: cog Utility."""

import discord.ext.test as dpytest
import pytest

pytestmark = pytest.mark.asyncio


async def test_userinfo_default(bot):
    await dpytest.message("<userinfo")
    msg = dpytest.get_message()
    assert msg.embeds
    field_names = {f.name for f in msg.embeds[0].fields}
    assert "ID" in field_names
    assert "Cuenta creada" in field_names


async def test_serverinfo(bot):
    await dpytest.message("<serverinfo")
    msg = dpytest.get_message()
    assert msg.embeds
    assert msg.embeds[0].title


async def test_avatar_default(bot):
    await dpytest.message("<avatar")
    msg = dpytest.get_message()
    assert msg.embeds
    assert "Avatar" in msg.embeds[0].title


async def test_poll_pocas_opciones(bot):
    await dpytest.message("<poll pregunta solo")
    msg = dpytest.get_message()
    assert "entre 2 y 10" in msg.content


async def test_poll_correcto(bot):
    await dpytest.message('<poll "¿Pizza o pasta?" pizza | pasta | sushi')
    msg = dpytest.get_message()
    assert msg.embeds
    assert "📊" in msg.embeds[0].title


async def test_recordatorio_formato_invalido(bot):
    await dpytest.message("<recordatorio mañana algo")
    msg = dpytest.get_message()
    assert "inválido" in msg.content.lower()
