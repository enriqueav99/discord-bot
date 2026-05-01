import asyncio
import random

import discord
import requests
from PIL import Image


def obtener_silueta(imagen):
    imagen = Image.open(imagen)
    imagen_gris = imagen.convert("L")
    umbral = 100
    imagen_silueta = imagen_gris.point(lambda p: 0 if p < umbral else 255)
    imagen_final = Image.new("RGB", imagen.size, "black")
    imagen_final.paste(imagen_silueta, (0, 0), imagen_silueta)
    return imagen_final


async def adivinar_pokemon(ctx, bot):
    poke_api_url = "https://pokeapi.co/api/v2/pokemon/"
    pokemon_id = random.randint(1, 898)

    loop = asyncio.get_running_loop()
    try:
        pokemon_data = await loop.run_in_executor(
            None, lambda: requests.get(f"{poke_api_url}{pokemon_id}", timeout=10).json()
        )
    except Exception as e:
        await ctx.send(f"No pude obtener el Pokémon: {e}")
        return

    pokemon_name = pokemon_data["name"].capitalize()
    pokemon_image_url = pokemon_data["sprites"]["front_default"]

    await ctx.send("Adivina este Pokémon, tienes 30 segundos!")

    image_resp = await loop.run_in_executor(
        None, lambda: requests.get(pokemon_image_url, timeout=10)
    )
    with open("img/pokemon_temp.png", "wb") as file:
        file.write(image_resp.content)

    imagen_silueta = obtener_silueta("img/pokemon_temp.png")
    imagen_silueta.save("img/silueta_pokemon.png")

    with open("img/silueta_pokemon.png", "rb") as file:
        await ctx.send(file=discord.File(file))

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        response = await bot.wait_for("message", check=check, timeout=30)
        if response.content.lower() == pokemon_name.lower():
            await ctx.send(f"¡Correcto, {ctx.author}! ¡Has adivinado el Pokémon!")
        else:
            await ctx.send(
                f"¡Incorrecto, {ctx.author}! El Pokémon correcto era {pokemon_name}."
            )
    except asyncio.TimeoutError:
        await ctx.send(f"Se acabó el tiempo. El Pokémon era {pokemon_name}.")
