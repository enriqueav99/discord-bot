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
            help_command=None,
        )
        self.config = config
        self.start_time = discord.utils.utcnow()
        self.dj_role_name = config.dj_role_name

    def _is_moderation_command(self, command: commands.Command | None) -> bool:
        return bool(command and getattr(command.cog, "qualified_name", None) == "Moderation")

    def _has_dj_role(self, member: discord.abc.User | discord.Member | None) -> bool:
        if not isinstance(member, discord.Member):
            return False
        return any(role.name == self.dj_role_name for role in member.roles)

    def _dj_role_error(self) -> str:
        return f"❌ Necesitas el rol **{self.dj_role_name}** para usar este comando."

    async def setup_hook(self) -> None:
        self.add_check(self._prefix_command_check)
        self.tree.add_check(self._app_command_check)
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
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="/help")
        )
        canal_bots = self.get_channel(self.config.id_canal_bots)
        if canal_bots:
            with contextlib.suppress(discord.HTTPException):
                await canal_bots.send(f"✅ Conectado como {self.user} y listo.")
        canal_logs = (
            self.get_channel(self.config.id_canal_logs) if self.config.id_canal_logs else None
        )
        if canal_logs:
            ts = discord.utils.format_dt(discord.utils.utcnow())
            with contextlib.suppress(discord.HTTPException):
                await canal_logs.send(f"🟢 Bot iniciado — {self.user} conectado a Discord {ts}")

    async def on_disconnect(self):
        log.warning("Bot desconectado de Discord")
        canal_logs = (
            self.get_channel(self.config.id_canal_logs) if self.config.id_canal_logs else None
        )
        if canal_logs:
            ts = discord.utils.format_dt(discord.utils.utcnow())
            with contextlib.suppress(discord.HTTPException):
                await canal_logs.send(f"🔴 Bot desconectado de Discord {ts}")

    async def _prefix_command_check(self, ctx: commands.Context) -> bool:
        if self._is_moderation_command(ctx.command):
            return True
        if self._has_dj_role(ctx.author):
            return True
        raise commands.CheckFailure(self._dj_role_error())

    async def _app_command_check(self, interaction: discord.Interaction) -> bool:
        command = interaction.command
        if (
            command
            and getattr(getattr(command, "binding", None), "qualified_name", None) == "Moderation"
        ):
            return True
        if self._has_dj_role(interaction.user):
            return True
        message = self._dj_role_error()
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return False

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CheckFailure):
            if ctx.interaction:
                await ctx.send(str(error), ephemeral=True)
            else:
                await ctx.send(str(error))
            return
        await super().on_command_error(ctx, error)


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
