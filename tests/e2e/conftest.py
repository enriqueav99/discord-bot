"""Fixtures para tests E2E con dpytest.

dpytest mockea por completo el gateway de Discord y los HTTP del cliente,
así que podemos disparar comandos reales sin conectarnos a Discord.
"""

from __future__ import annotations

import discord
import discord.ext.test as dpytest
import pytest_asyncio
from discord.ext import commands

from cogs import EXTENSIONS
from src.config import BotConfig


class _BotForTest(commands.Bot):
    def __init__(self, config: BotConfig):
        intents = discord.Intents.all()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=config.prefix, intents=intents)
        self.config = config

    async def setup_hook(self) -> None:
        for ext in EXTENSIONS:
            # 'voice' usa subprocess+ffmpeg y 'events' inserta un handler global
            # de errores que tragaría las assertions; los excluimos de E2E.
            if ext in {"cogs.voice", "cogs.events"}:
                continue
            await self.load_extension(ext)


@pytest_asyncio.fixture
async def bot():
    config = BotConfig(
        token="dummy",
        prefix="<",
        id_canal_principal=1,
        id_canal_bots=2,
        cam_device=None,
    )
    b = _BotForTest(config)
    await b._async_setup_hook()
    await b.setup_hook()

    dpytest.configure(b)
    yield b

    await dpytest.empty_queue()
    await b.close()
