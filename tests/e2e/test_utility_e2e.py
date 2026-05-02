"""E2E: cog Utility."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_userinfo_default(harness):
    result = await harness.invoke("userinfo", miembro=None)
    assert result.embeds
    field_names = {f.name for f in result.embeds[0].fields}
    assert "ID" in field_names
    assert "Cuenta creada" in field_names


async def test_serverinfo(harness):
    result = await harness.invoke("serverinfo")
    assert result.embeds
    assert result.embeds[0].title


async def test_avatar_default(harness):
    result = await harness.invoke("avatar", miembro=None)
    assert result.embeds
    assert "Avatar" in result.embeds[0].title


async def test_poll_pocas_opciones(harness):
    result = await harness.invoke("poll", "pregunta", opciones="solo")
    assert "entre 2 y 10" in result.all_text


async def test_poll_correcto(harness):
    result = await harness.invoke("poll", "¿Pizza o pasta?", opciones="pizza | pasta | sushi")
    assert result.embeds
    assert "📊" in result.embeds[0].title


async def test_recordatorio_formato_invalido(harness):
    result = await harness.invoke("recordatorio", "mañana", mensaje="algo")
    assert "inválido" in result.all_text.lower()
