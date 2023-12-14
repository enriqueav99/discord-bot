import discord
from discord.ext import commands
import json
import os
import youtube_dl
from src.logger import start_logger
start_logger()


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

@bot.event
async def on_disconnect():
    canal_texto_id = id_canal_bots  # ID del canal donde enviar el mensaje
    canal_texto = bot.get_channel(canal_texto_id)
    if canal_texto:
        await canal_texto.send('¡El bot se ha desconectado!')
    else:
        print('No se pudo encontrar el canal para enviar el mensaje de despedida.')


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


# Función para reproducir audio desde YouTube
async def reproducir_audio(ctx, url):
    canal_voz = ctx.author.voice.channel
    if canal_voz:
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['formats'][0]['url']
                canal_voz = await canal_voz.connect()
                canal_voz.play(discord.FFmpegPCMAudio(url2, **ydl_opts))
                await ctx.send(f'Reproduciendo: {info["title"]} en {canal_voz}')
        except Exception as e:
            await ctx.send("Ocurrió un error al reproducir el audio.")
            print(e)
    else:
        await ctx.send("Debes estar en un canal de voz para usar este comando.")

# Comando para reproducir una canción de YouTube
@bot.command()
async def reproducir(ctx, *, url: str):
    await reproducir_audio(ctx, url)

# Manejador de errores para el comando de reproducción de canciones
@reproducir.error
async def reproducir_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Por favor, proporciona un enlace de YouTube.')

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

# Reemplaza 'TOKEN' con tu token de bot de Discord
bot.run(token)
