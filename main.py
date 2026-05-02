from random import random
from src.commands import *
import discord
from discord.ext import commands
import json
import os
import requests
from src.logger import start_logger
from src.leer_csv import comprobar_whitelist
import random
from src.poke_func import adivinar_pokemon
from src.info import definir_info
from src.aloe import foto_aloe
import yt_dlp
import asyncio

start_logger()


# Get variables.json
with open("variables.json", "r") as config:
    data = json.load(config)
    token = os.getenv("DISCORD_BOT_TOKEN") or data.get("token")
    prefix = os.getenv("DISCORD_BOT_PREFIX") or data.get("prefix")
    id_canal_principal = data["id_canal_principal"],
    id_canal_bots = data["id_canal_bots"]

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=prefix, intents = intents, description="Bot de Korea")

@bot.event
async def on_ready():
    for vc in bot.voice_clients:
        await vc.disconnect(force=True)
    general_channel = bot.get_channel(id_canal_bots)
    await general_channel.send(f'Conectado como {bot.user}, listo para ser utilizado, como ella hizo conmingo')

@bot.event
async def on_member_join(member):
    # Obtén el canal de bienvenida del servidor
    # Reemplaza CHANNEL_ID con el ID del canal donde quieres enviar el mensaje de bienvenida
    welcome_channel = bot.get_channel(id_canal_principal)

    # Envía un mensaje de bienvenida al canal
    if welcome_channel:
        await welcome_channel.send(f'{member.mention} entró al servidor, ya me joderia.')


@bot.command()
async def saludar(ctx):
    await ctx.send('Hola, que viva la saltisima trinidad, aqui el admin abuse no existe')

@bot.command()
async def ping(ctx):
    await ctx.send('pong')

@bot.command()
async def info(ctx):
    embed= definir_info()
    await ctx.send(embed=embed)

@bot.command()
async def join(ctx):
    if ctx.author.voice is None:
        await ctx.send("Debes estar en un canal de voz para usar este comando.")
        return
    canal_voz = ctx.author.voice.channel
    try:
        vc = ctx.guild.voice_client
        if vc is not None:
            if vc.channel.id == canal_voz.id:
                await ctx.send(f"Ya estoy en '{canal_voz}'")
                return
            await vc.move_to(canal_voz)
            await ctx.send(f"Me he movido a '{canal_voz}'")
        else:
            await canal_voz.connect(reconnect=False)
            await ctx.send(f"Me he unido a '{canal_voz}'")
    except discord.errors.ConnectionClosed as e:
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect(force=True)
        await ctx.send(f"No se pudo conectar al canal de voz (error {e.code}). Discord tiene una sesión anterior activa — espera ~30 segundos e inténtalo de nuevo.")
    except Exception as e:
        await ctx.send(f"Ocurrió un error: {e}")

@bot.command()
async def leave(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
    else:
        await ctx.send('No estoy en un canal de voz, no me molestes o llamo a Tomás.')


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
async def play(ctx, *, url: str):
    if ctx.author.voice is None:
        await ctx.send("¡Debes estar en un canal de voz para usar este comando!")
        return

    voice_channel = ctx.author.voice.channel
    try:
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(voice_channel)
        else:
            await voice_channel.connect(reconnect=False)
    except discord.errors.ConnectionClosed as e:
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect(force=True)
        await ctx.send(f"No se pudo conectar al canal de voz (error {e.code}). Espera ~30 segundos e inténtalo de nuevo.")
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    loop = asyncio.get_event_loop()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))

        if info is None:
            await ctx.send("No se pudo obtener información del video.")
            return

        if 'entries' in info:
            if not info['entries']:
                await ctx.send("No se encontraron resultados.")
                return
            info = info['entries'][0]

        audio_url = info['url']

        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }
        ctx.voice_client.play(discord.FFmpegPCMAudio(audio_url, executable='ffmpeg', **ffmpeg_opts))
        await ctx.send(f'Reproduciendo: {info["title"]}')

    except Exception as e:
        import traceback
        traceback.print_exc()
        await ctx.send(f"Error al reproducir: {e}")

@bot.command()
async def aloe(ctx):
    await foto_aloe(ctx, bot, id_canal_bots)


# Reemplaza 'TOKEN' con tu token de bot de Discord
bot.run(token)
