import discord
from discord.ext import commands
import json
import os
import youtube_dl
from src.logger import start_logger
from src.leer_csv import comprobar_whitelist
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
    print(f'Conectado como {bot.user}')

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
        await ctx.send('Me he desconectado del canal de voz.')
    else:
        await ctx.send('No estoy en un canal de voz, no me molestes o llamo a Tomás.')

async def rep_sonido(ctx):
    if comprobar_whitelist(ctx.author.name):
        canal_voz = bot.get_channel(265992324876730378)
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_connected():
            try:
                source = discord.FFmpegPCMAudio('sonidos/rickroll.mp3')  # Reemplaza con la ruta de tu archivo de audio
                voice_client.play(source)
                print("Sonido reproducido con éxito.")
            except Exception as e:
                await ctx.send(f"Ocurrió un error al reproducir el sonido: {e}")
        else:
            await ctx.send("Debo de estar en un canal de voz para usar este comando.")
    else:
        await ctx.send("Lo siento, no tienes permiso para usar este comando.")

    
@bot.command()
async def rr(ctx):
    await rep_sonido(ctx)
    
@bot.command
async def ir(ctx):
    file_path = 'img/ric.jpg'  # Reemplaza con la ruta de tu imagen
    
    # Intentar abrir la imagen
    try:
        with open(file_path, 'rb') as file:
            picture = discord.File(file)
            await message.channel.send(file=picture)
    except FileNotFoundError:
        await message.channel.send('No se pudo encontrar la imagen.')

# Reemplaza 'TOKEN' con tu token de bot de Discord
bot.run(token)
