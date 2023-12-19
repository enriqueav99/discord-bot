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
start_logger()


# Get variables.json
with open("variables.json", "r") as config:
    data = json.load(config)
    token = data["token"]
    prefix = data["prefix"]
    id_canal_principal = data["id_canal_principal"],
    id_canal_bots = data["id_canal_bots"]

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=prefix, intents = intents, description="Bot de Korea")

@bot.event
async def on_ready():
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
    canal_voz = ctx.author.voice.channel
    if canal_voz:
        try:
            await canal_voz.connect()
            await ctx.send(f"Me he unido a '{canal_voz}'")
        except discord.ClientException:
            await ctx.send("Ya estoy en un canal de voz.")
        except Exception as e:
            await ctx.send(f"Ocurrió un error: {e}")
    else:
        await ctx.send("Debes estar en un canal de voz para usar este comando.")

@bot.command()
async def leave(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
    else:
        await ctx.send('No estoy en un canal de voz, no me molestes o llamo a Tomás.')

 
@bot.command()
async def rr(ctx):
    await rep_sonido(bot, ctx)
    
@bot.command()
async def rick(ctx):
    await mandar_rick(bot, id_canal_bots)

@bot.command()
async def adivina(ctx):
    await adivinar_pokemon(ctx, bot)



# Reemplaza 'TOKEN' con tu token de bot de Discord
bot.run(token)
