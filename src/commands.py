import discord
from src.leer_csv import comprobar_whitelist
from src.leer_csv import comprobar_whitelist
import subprocess
import os


async def mandar_rick(bot, id):
    file_path = 'img/ric.jpg'  # Reemplaza con la ruta de tu imagen
    general_channel = bot.get_channel(id)
    # Intentar abrir la imagen
    try:
        with open(file_path, 'rb') as file:
            picture = discord.File(file)
            await general_channel.send(file=picture)
    except FileNotFoundError:
        await general_channel.send('No se pudo encontrar la imagen.')

async def rep_sonido(ctx):
    if comprobar_whitelist(ctx.author.name):
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
        await ctx.send("Lo siento, te jodes, no tienes permiso para usar este comando.")

