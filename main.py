import discord
from discord.ext import commands
import json
import os

import logging

# Guardar los logs en un archivo para su estudio
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


# Get variables.json
with open("variables.json", "r") as config:
    data = json.load(config)
    token = data["token"]
    prefix = data["prefix"]
    id_canal_principal = data["id_canal_principal"],
    id_canal_bots = data["id_canal_bots"]

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='>', intents = intents, description="Bot de Korea")

@bot.event
async def on_ready():
    general_channel = bot.get_channel(id_canal_bots)
    await general_channel.send(f'Conectado como {bot.user}, iniciando prueba')
    print(f'Conectado como {bot.user}')

@bot.command()
async def saludar(ctx):
    await ctx.send('Hola, que viva la saltisima trinidad, aqui el admin abuse no existe')

@bot.command()
async def ping(ctx):
    print('pong')
    await ctx.send('pong')
    
@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title="Bot de Korea",
        description="¡Bienvenido al Bot de Korea! Aquí tienes información sobre este bot.",
        color=0xff0000
    )
    embed.add_field(name="Autor", value="enriqueav99", inline=False)
    embed.add_field(name="Versión", value="0.1.0", inline=False)
    embed.add_field(name="Descripción", value="Bot koreano para que por fin alguien ponga orden aquí, algunas funciones tendrán whitelist.", inline=False)
    embed.add_field(name="Comandos", value="Lista de comandos disponibles:", inline=False)
    embed.add_field(name=">saludar", value="Saluda al bot.", inline=True)
    embed.add_field(name=">ping", value="Obtener respuesta 'pong'.", inline=True)
    embed.add_field(name=">info", value="Muestra este mensaje de información.", inline=True)
    # Añade más campos según los comandos que tengas en tu bot

    embed.set_footer(text="Usa el bot con responsabilidad")

    await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    # Obtén el canal de bienvenida del servidor
    # Reemplaza CHANNEL_ID con el ID del canal donde quieres enviar el mensaje de bienvenida
    welcome_channel = bot.get_channel(id_canal_principal)

    # Envía un mensaje de bienvenida al canal
    if welcome_channel:
        await welcome_channel.send(f'{member.mention} entró al servidor, ya me joderia.')


# Reemplaza 'TOKEN' con tu token de bot de Discord
bot.run(token)
