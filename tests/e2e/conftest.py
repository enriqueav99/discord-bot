"""Fixtures E2E.

dpytest tiene problemas de compatibilidad con discord.py 2.4+, así que en
lugar de mockear el gateway entero, usamos un harness propio que:

1. Carga el `Bot` real con todos los cogs (sin conectarse a Discord).
2. Construye un `Context` mockeado con todas las primitivas que los comandos
   necesitan (send, defer, author, channel, guild, voice_client, etc.).
3. Invoca el callback del comando como lo haría discord.py tras parsear
   un mensaje. Eso ejercita todo el código de los cogs end-to-end sin red.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest_asyncio
from discord.ext import commands

from cogs import EXTENSIONS
from src.config import BotConfig


class _BotForTest(commands.Bot):
    def __init__(self, config: BotConfig):
        intents = discord.Intents.all()
        super().__init__(command_prefix=config.prefix, intents=intents, help_command=None)
        self.config = config

    async def setup_hook(self) -> None:
        for ext in EXTENSIONS:
            # voice usa subprocess+ffmpeg y events tiene un error handler global
            # que tragaría las assertions; los excluimos del bot de tests.
            if ext in {"cogs.voice", "cogs.events"}:
                continue
            await self.load_extension(ext)

    @property
    def latency(self) -> float:
        # Sin gateway abierto, la latencia real sería NaN.
        return 0.05


@dataclass
class InvokeResult:
    """Resultado de invocar un comando: lista de mensajes/embeds enviados al ctx."""

    ctx: MagicMock

    @property
    def messages(self) -> list[str]:
        return [
            (call.args[0] if call.args else "") or ""
            for call in self.ctx.send.call_args_list
            if call.args
        ]

    @property
    def embeds(self) -> list[discord.Embed]:
        result = []
        for call in self.ctx.send.call_args_list:
            embed = call.kwargs.get("embed")
            if embed is None and call.args:
                emb_pos = call.args[0] if isinstance(call.args[0], discord.Embed) else None
                if emb_pos:
                    embed = emb_pos
            if embed is not None:
                result.append(embed)
        return result

    @property
    def all_text(self) -> str:
        out = list(self.messages)
        for e in self.embeds:
            if e.title:
                out.append(e.title)
            if e.description:
                out.append(e.description)
            for f in e.fields:
                out.append(f"{f.name}: {f.value}")
            if e.footer and e.footer.text:
                out.append(e.footer.text)
        return "\n".join(out)


class Harness:
    """Invoca callbacks de comandos sobre el bot con un Context mockeado."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _make_ctx(self, *, member_perms: dict[str, bool] | None = None) -> MagicMock:
        ctx = MagicMock(spec=commands.Context)
        ctx.bot = self.bot
        ctx.send = AsyncMock(return_value=MagicMock(spec=discord.Message))
        ctx.defer = AsyncMock()
        ctx.reply = AsyncMock()
        ctx.interaction = None

        guild = MagicMock(spec=discord.Guild)
        guild.id = 100
        guild.name = "Servidor Test"
        guild.member_count = 5
        guild.channels = []
        guild.roles = []
        guild.premium_tier = 0
        guild.created_at = discord.utils.utcnow()
        guild.icon = None
        guild.owner = None
        guild.default_role = MagicMock()
        guild.voice_client = None
        guild.get_member = MagicMock(return_value=None)

        author = MagicMock(spec=discord.Member)
        author.id = 999
        author.name = "tester"
        author.display_name = "tester"
        author.mention = "<@999>"
        author.bot = False
        author.color = discord.Color.default()
        author.created_at = discord.utils.utcnow()
        author.joined_at = discord.utils.utcnow()
        dj_role = MagicMock()
        dj_role.name = "DJ"
        author.roles = [guild.default_role, dj_role]
        author.display_avatar = MagicMock()
        author.display_avatar.url = "https://avatar.test/x.png"
        author.voice = None
        author.guild_permissions = MagicMock(**dict.fromkeys(member_perms or {}, True))
        # has_permissions check usa author.guild_permissions
        if member_perms:
            for name, value in member_perms.items():
                setattr(author.guild_permissions, name, value)
        else:
            for name in (
                "manage_messages",
                "kick_members",
                "ban_members",
                "moderate_members",
            ):
                setattr(author.guild_permissions, name, True)

        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 555
        channel.mention = "<#555>"
        channel.send = AsyncMock(return_value=MagicMock(spec=discord.Message))

        ctx.author = author
        ctx.guild = guild
        ctx.channel = channel
        ctx.message = MagicMock()
        ctx.message.delete = AsyncMock()
        ctx.voice_client = None
        return ctx

    async def invoke(
        self, command_name: str, *args: Any, member_perms: dict | None = None, **kwargs: Any
    ) -> InvokeResult:
        cmd = self.bot.get_command(command_name)
        if cmd is None:
            raise AssertionError(f"Comando {command_name!r} no registrado")
        ctx = self._make_ctx(member_perms=member_perms)
        try:
            await cmd.callback(cmd.cog, ctx, *args, **kwargs)
        except commands.MissingPermissions:
            # Permitimos que los tests verifiquen los chequeos de permisos.
            await ctx.send("Sin permisos.")
        return InvokeResult(ctx=ctx)


@pytest_asyncio.fixture
async def bot():
    config = BotConfig(
        token="dummy",
        prefix="<",
        id_canal_principal=1,
        id_canal_bots=2,
        id_canal_logs=None,
        dj_role_name="DJ",
    )
    b = _BotForTest(config)
    await b._async_setup_hook()
    await b.setup_hook()
    try:
        yield b
    finally:
        await b.close()


@pytest_asyncio.fixture
async def harness(bot):
    return Harness(bot)
