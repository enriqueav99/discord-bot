"""E2E: cog Music sin red ni ffmpeg (solo flujo de comandos sobre la cola)."""

from collections import deque

import discord.ext.test as dpytest
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


async def test_queue_vacia(bot):
    await dpytest.message("<queue")
    msg = dpytest.get_message()
    assert "vacía" in msg.content.lower()


async def test_queue_con_canciones(bot):
    music = bot.get_cog("Music")
    player = music.get_player(dpytest.get_config().guilds[0].id)
    player.queue = deque([_track("Bohemian Rhapsody"), _track("Wonderwall")])

    await dpytest.message("<queue")
    msg = dpytest.get_message()
    assert msg.embeds
    descripcion = " ".join(f.value for f in msg.embeds[0].fields)
    assert "Bohemian Rhapsody" in descripcion
    assert "Wonderwall" in descripcion


async def test_clearqueue(bot):
    music = bot.get_cog("Music")
    player = music.get_player(dpytest.get_config().guilds[0].id)
    player.queue = deque([_track("a"), _track("b"), _track("c")])

    await dpytest.message("<clearqueue")
    msg = dpytest.get_message()
    assert "3" in msg.content
    assert len(player.queue) == 0


async def test_remove_posicion_invalida(bot):
    music = bot.get_cog("Music")
    player = music.get_player(dpytest.get_config().guilds[0].id)
    player.queue = deque([_track("a")])

    await dpytest.message("<remove 99")
    msg = dpytest.get_message()
    assert "inválida" in msg.content


async def test_remove_correcto(bot):
    music = bot.get_cog("Music")
    player = music.get_player(dpytest.get_config().guilds[0].id)
    player.queue = deque([_track("a"), _track("b"), _track("c")])

    await dpytest.message("<remove 2")
    msg = dpytest.get_message()
    assert "b" in msg.content
    titulos = [t.title for t in player.queue]
    assert titulos == ["a", "c"]


async def test_shuffle_pocas(bot):
    await dpytest.message("<shuffle")
    msg = dpytest.get_message()
    assert "al menos 2" in msg.content


async def test_loop_mode_track(bot):
    await dpytest.message("<loop track")
    msg = dpytest.get_message()
    assert "track" in msg.content
    music = bot.get_cog("Music")
    player = music.get_player(dpytest.get_config().guilds[0].id)
    assert player.loop_mode == LoopMode.TRACK


async def test_volume_fuera_de_rango(bot):
    await dpytest.message("<volume 9999")
    msg = dpytest.get_message()
    assert "0 y 200" in msg.content


async def test_nowplaying_nada(bot):
    await dpytest.message("<nowplaying")
    msg = dpytest.get_message()
    assert "No hay nada" in msg.content
