import discord
from discord.ext import commands
import json
import os

# Get variables.json
with open("variables.json", "r") as config:
    data = json.load(config)
    token = data["token"]
    prefix = data["prefix"]
    id_canal_principal = data["id_canal_principal"],
    id_canal_bots = data["id_canal_bots"]

intents = discord.Intents.default()
intents.messages = True  # Mensajes
intents.guilds = True  # Servidores
intents.members = True  # Miembros
intents.bans = True  # Baneos
intents.emojis = True  # Emojis
intents.reactions = True  # Reacciones
intents.voice_states = True 

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
    embed=discord.Embed(title="title", description="description", color=0xff0000)
    embed.add_field(name="field", value="value", inline=False)
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