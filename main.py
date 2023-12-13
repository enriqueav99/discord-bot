import discord
from discord.ext import commands
import json
import os



# Get configuration.json
with open("variables.json", "r") as config:
    data = json.load(config)
    token = data["token"]
    prefix = data["prefix"]
    id_canal_principal = data["id_canal_principal"]

intents = discord.Intents.default()
intents.members = True 


bot = commands.Bot(prefix, intents = intents)


@bot.event
async def on_ready():
    print(f'Conectado como {bot.user}')

@bot.command()
async def saludar(ctx):
    general_channel = ctx.guild.get_channel(ctx.guild.id)
    await general_channel.send('Hola, que viva la saltisima trinidad, aqui el admin abuse no existe')


@bot.event
async def on_member_join(member):
    # Obtén el canal de bienvenida del servidor
    # Reemplaza CHANNEL_ID con el ID del canal donde quieres enviar el mensaje de bienvenida
    welcome_channel = bot.get_channel(id_canal_principal)

    # Envía un mensaje de bienvenida al canal
    if welcome_channel:
        await welcome_channel.send(f'Bienvenido {member.mention} al servidor. ¡Esperamos que disfrutes tu estancia, SUBNORMAL!')


# Reemplaza 'TOKEN' con tu token de bot de Discord
bot.run(token)