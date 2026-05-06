import discord


def definir_info():
    embed = discord.Embed(
        title="Bot de Korea",
        description="¡Bienvenido al Bot de Korea!",
        color=0xFF0000,
    )
    embed.add_field(name="Autor", value="enriqueav99", inline=False)
    embed.add_field(name="Versión", value="0.3.0", inline=False)
    embed.add_field(
        name="Descripción",
        value="Bot koreano para que por fin alguien ponga orden aquí.",
        inline=False,
    )
    embed.set_footer(text="Usa el bot con responsabilidad")
    return embed
