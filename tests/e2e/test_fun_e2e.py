"""E2E: cog Fun."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_8ball(harness):
    result = await harness.invoke("8ball", pregunta="¿gana hoy el madrid?")
    assert "🎱" in result.all_text


async def test_dado_default(harness):
    result = await harness.invoke("dado")
    assert "🎲" in result.all_text


async def test_dado_caras_invalidas(harness):
    result = await harness.invoke("dado", caras=1)
    assert "entre 2 y 1000" in result.all_text


async def test_moneda(harness):
    result = await harness.invoke("moneda")
    assert "Cara" in result.all_text or "Cruz" in result.all_text


async def test_choose_pocas_opciones(harness):
    result = await harness.invoke("choose", opciones="solo_una")
    assert "al menos 2" in result.all_text


async def test_choose_funciona(harness):
    result = await harness.invoke("choose", opciones="pizza | pasta | sushi")
    assert any(opt in result.all_text for opt in ["pizza", "pasta", "sushi"])
