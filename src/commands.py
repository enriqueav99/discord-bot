import discord

from src.leer_csv import comprobar_whitelist


async def mandar_rick(bot, id):
    file_path = "img/ric.jpg"
    general_channel = bot.get_channel(id)
    if general_channel is None:
        return
    try:
        with open(file_path, "rb") as file:
            await general_channel.send(file=discord.File(file))
    except FileNotFoundError:
        await general_channel.send("No se pudo encontrar la imagen.")


async def rep_sonido(ctx):
    if not comprobar_whitelist(ctx.author.name):
        await ctx.send("Lo siento, te jodes, no tienes permiso para usar este comando.")
        return

    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("Debo de estar en un canal de voz para usar este comando.")
        return

    try:
        source = discord.FFmpegPCMAudio("sonidos/rickroll.mp3")
        if voice_client.is_playing():
            voice_client.stop()
        voice_client.play(source)
    except Exception as e:
        await ctx.send(f"Ocurrió un error al reproducir el sonido: {e}")
