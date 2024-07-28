import discord
from src.leer_csv import comprobar_whitelist
from src.leer_csv import comprobar_whitelist
import subprocess
import os
def tomar_foto():
    filename = '/tmp/aloe.jpg'
    command = [
        'ffmpeg',
        '-y',  # Overwrite output file if it exists
        '-f', 'v4l2',
        '-i', '/dev/video0',
        '-frames:v', '1',  # Capture a single frame
        filename
    ]

    try:
        subprocess.run(command, check=True)
        return filename
    except subprocess.CalledProcessError:
        return None

async def foto_aloe(ctx, bot, canal):
    if comprobar_whitelist(ctx.author.name):
        filename = tomar_foto()
        if filename:
            channel = bot.get_channel(canal)
            await channel.send(file=discord.File(filename))
            #await ctx.send("Foto tomada y enviada al canal.")
            #os.remove(filename)  # Limpiar el archivo temporal
        else:
            await ctx.send("Error al tomar la foto.")
    else:
        await ctx.send("Lo siento, te jodes, no tienes permiso para usar este comando.")

