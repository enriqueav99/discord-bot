import discord
def definir_info():
    embed = discord.Embed(
        title="Bot de Korea",
        description="¡Bienvenido al Bot de Korea! Aquí tienes información sobre este bot.",
        color=0xff0000
    )
    embed.add_field(name="Autor", value="enriqueav99", inline=False)
    embed.add_field(name="Versión", value="0.2.0", inline=False)
    embed.add_field(name="Descripción", value="Bot koreano para que por fin alguien ponga orden aquí, algunas funciones tendrán whitelist.", inline=False)
    embed.add_field(name="Comandos", value="Lista de comandos disponibles:", inline=False)
    embed.add_field(name="<saludar", value="Saluda al bot.", inline=True)
    embed.add_field(name="<ping", value="Obtener respuesta 'pong'.", inline=True)
    embed.add_field(name="<info", value="Muestra este mensaje de información.", inline=False)
    embed.add_field(name="<adivina", value="Adivina cual es el pokemon de la imagen en 30 segundos.", inline=True)
    # Añade más campos según los comandos que tengas en tu bot

    embed.set_footer(text="Usa el bot con responsabilidad")
    return embed
