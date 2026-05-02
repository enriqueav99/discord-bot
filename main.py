"""Punto de entrada del Bot de Korea."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from pathlib import Path

import discord
from discord.ext import commands, tasks

from cogs import EXTENSIONS
from src.config import BotConfig
from src.logger import start_logger

HEARTBEAT_FILE = Path("/tmp/.bot_alive")

log = logging.getLogger("discord.bot")


class KoreaBot(commands.Bot):
    def __init__(self, config: BotConfig):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=config.prefix,
            intents=intents,
            description="Bot de Korea",
        )
        self.config = config

    async def setup_hook(self) -> None:
        self.heartbeat.start()
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info("Extensión cargada: %s", ext)
            except Exception:
                log.exception("Error cargando %s", ext)
        try:
            synced = await self.tree.sync()
            log.info("Sincronizados %d slash commands", len(synced))
        except Exception:
            log.exception("Error sincronizando slash commands")

    @tasks.loop(seconds=30)
    async def heartbeat(self):
        with contextlib.suppress(OSError):
            HEARTBEAT_FILE.write_text(str(int(time.time())))

    @heartbeat.before_loop
    async def _before_heartbeat(self):
        await self.wait_until_ready()

    async def on_ready(self):
        log.info("Conectado como %s (id=%s)", self.user, self.user.id)
        canal = self.get_channel(self.config.id_canal_bots)
        if canal:
            with contextlib.suppress(discord.HTTPException):
                await canal.send(
                    f"Conectado como {self.user}, listo para ser utilizado, como ella hizo conmigo"
                )


def _ensure_opus() -> None:
    if discord.opus.is_loaded():
        return
    for name in ("libopus.so.0", "libopus.so", "opus"):
        try:
            discord.opus.load_opus(name)
            log.info("libopus cargado: %s", name)
            return
        except OSError:
            continue
    log.warning("libopus no se pudo cargar; la reproducción de voz no tendrá audio")


async def main():
    start_logger()
    _ensure_opus()
    config = BotConfig.load()
    async with KoreaBot(config) as bot:
        await bot.start(config.token, reconnect=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot detenido por el usuario")
