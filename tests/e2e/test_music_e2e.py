"""E2E: cog Music sin red ni ffmpeg (solo flujo de comandos sobre la cola)."""

from collections import deque

import pytest

from cogs.music import LoopMode, Track

pytestmark = pytest.mark.asyncio


def _track(title: str = "Una canción") -> Track:
    return Track(
        title=title,
        url="http://stream/test",
        requested_by="tester",
        text_channel_id=1,
        duration=180,
    )


async def test_queue_vacia(harness):
    result = await harness.invoke("queue")
    assert "vacía" in result.all_text.lower()


async def test_queue_con_canciones(harness):
    music = harness.bot.get_cog("Music")
    player = music.get_player(100)
    player.queue = deque([_track("Bohemian Rhapsody"), _track("Wonderwall")])

    result = await harness.invoke("queue")
    assert result.embeds
    assert "Bohemian Rhapsody" in result.all_text
    assert "Wonderwall" in result.all_text


async def test_clearqueue(harness):
    music = harness.bot.get_cog("Music")
    player = music.get_player(100)
    player.queue = deque([_track("a"), _track("b"), _track("c")])

    result = await harness.invoke("clearqueue")
    assert "3" in result.all_text
    assert len(player.queue) == 0


async def test_remove_posicion_invalida(harness):
    music = harness.bot.get_cog("Music")
    player = music.get_player(100)
    player.queue = deque([_track("a")])

    result = await harness.invoke("remove", posicion=99)
    assert "inválida" in result.all_text


async def test_remove_correcto(harness):
    music = harness.bot.get_cog("Music")
    player = music.get_player(100)
    player.queue = deque([_track("a"), _track("b"), _track("c")])

    result = await harness.invoke("remove", posicion=2)
    assert "b" in result.all_text
    assert [t.title for t in player.queue] == ["a", "c"]


async def test_shuffle_pocas(harness):
    music = harness.bot.get_cog("Music")
    music.get_player(100).queue = deque()
    result = await harness.invoke("shuffle")
    assert "al menos 2" in result.all_text


async def test_loop_mode_track(harness):
    result = await harness.invoke("loop", modo="track")
    assert "track" in result.all_text
    music = harness.bot.get_cog("Music")
    # Comparar por .value evita problemas si el módulo se reimporta y
    # el Enum tiene identidad de clase distinta entre conftest y test.
    assert music.get_player(100).loop_mode.value == LoopMode.TRACK.value


async def test_volume_fuera_de_rango(harness):
    result = await harness.invoke("volume", nivel=9999)
    assert "0 y 200" in result.all_text


async def test_nowplaying_nada(harness):
    result = await harness.invoke("nowplaying")
    assert "No hay nada" in result.all_text
