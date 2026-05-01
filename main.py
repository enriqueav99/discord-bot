import asyncio
import json
import os
import random

import discord
import yt_dlp
from discord.ext import commands

from src.aloe import foto_aloe
from src.commands import mandar_rick, rep_sonido
from src.info import definir_info
from src.logger import start_logger
from src.poke_func import adivinar_pokemon

start_logger()

with open("variables.json", "r") as config:
    data = json.load(config)

token = os.getenv("DISCORD_BOT_TOKEN")
prefix = os.getenv("DISCORD_BOT_PREFIX", "!")

if not token:
    raise RuntimeError("DISCORD_BOT_TOKEN no está definido en el entorno")

id_canal_principal = int(data["id_canal_principal"])
id_canal_bots = int(data["id_canal_bots"])

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=prefix, intents=intents, description="Bot de Korea")


@bot.event
async def on_ready():
    print(f"Conectado como {bot.user} (id={bot.user.id})")
    canal = bot.get_channel(id_canal_bots)
    if canal:
        await canal.send(
            f"Conectado como {bot.user}, listo para ser utilizado, como ella hizo conmigo"
        )


@bot.event
async def on_member_join(member):
    welcome_channel = bot.get_channel(id_canal_principal)
    if welcome_channel:
        await welcome_channel.send(f"{member.mention} entró al servidor, ya me joderia.")


@bot.command()
async def saludar(ctx):
    await ctx.send("Hola, que viva la saltisima trinidad, aqui el admin abuse no existe")


@bot.command()
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"pong ({latency_ms} ms)")


@bot.command()
async def info(ctx):
    embed = definir_info()
    await ctx.send(embed=embed)


@bot.command()
async def join(ctx):
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("Debes estar en un canal de voz para usar este comando.")
        return
    canal_voz = ctx.author.voice.channel
    try:
        if ctx.voice_client is None:
            await canal_voz.connect()
        else:
            await ctx.voice_client.move_to(canal_voz)
        await ctx.send(f"Me he unido a '{canal_voz}'")
    except discord.ClientException:
        await ctx.send("Ya estoy en un canal de voz.")
    except Exception as e:
        await ctx.send(f"Ocurrió un error: {e}")


@bot.command()
async def leave(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
    else:
        await ctx.send("No estoy en un canal de voz, no me molestes o llamo a Tomás.")


@bot.command()
async def rr(ctx):
    await rep_sonido(ctx)


@bot.command()
async def rick(ctx):
    await mandar_rick(bot, id_canal_bots)


@bot.command()
async def adivina(ctx):
    await adivinar_pokemon(ctx, bot)


@bot.command()
async def play(ctx, url: str):
    if ctx.author.voice is None:
        await ctx.send("¡Debes estar en un canal de voz para usar este comando!")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()
    else:
        await ctx.voice_client.move_to(voice_channel)

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch",
    }

    loop = asyncio.get_running_loop()

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info_dict = await loop.run_in_executor(None, _extract)
    except Exception as e:
        await ctx.send(f"No pude obtener el audio: {e}")
        return

    if "entries" in info_dict:
        info_dict = info_dict["entries"][0]

    stream_url = info_dict["url"]
    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    ctx.voice_client.play(source)

    await ctx.send(f'Reproduciendo audio de: {info_dict.get("title", "desconocido")}')


@bot.command()
async def aloe(ctx):
    await foto_aloe(ctx, bot, id_canal_bots)


if __name__ == "__main__":
    bot.run(token, reconnect=True)
