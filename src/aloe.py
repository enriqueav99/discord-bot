import os
import subprocess

import discord

from src.leer_csv import comprobar_whitelist


def tomar_foto():
    filename = "/tmp/aloe.jpg"
    cam = os.getenv("DISCORD_BOT_CAM")
    if not cam:
        return None
    command = [
        "ffmpeg",
        "-y",
        "-f", "v4l2",
        "-i", cam,
        "-frames:v", "1",
        filename,
    ]
    try:
        subprocess.run(command, check=True)
        return filename
    except subprocess.CalledProcessError:
        return None


async def foto_aloe(ctx, bot, canal):
    if not comprobar_whitelist(ctx.author.name):
        await ctx.send("Lo siento, te jodes, no tienes permiso para usar este comando.")
        return

    filename = tomar_foto()
    if not filename:
        await ctx.send("Error al tomar la foto.")
        return

    channel = bot.get_channel(canal)
    if channel:
        await channel.send(file=discord.File(filename))
