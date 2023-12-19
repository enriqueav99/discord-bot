from PIL import Image
import discord
from src.leer_csv import comprobar_whitelist
from src.leer_csv import comprobar_whitelist
import random
import requests



def obtener_silueta(imagen):
    imagen = Image.open(imagen)
    # Convertir la imagen a escala de grises
    imagen_gris = imagen.convert("L")
    # Obtener la silueta aplicando umbral
    umbral = 100  # Puedes ajustar este valor según la imagen
    imagen_silueta = imagen_gris.point(lambda p: 0 if p < umbral else 255)
    # Convertir a una imagen con fondo negro
    imagen_final = Image.new("RGB", imagen.size, "black")
    imagen_final.paste(imagen_silueta, (0, 0), imagen_silueta)
    return imagen_final



async def adivinar_pokemon(ctx, bot):

    poke_api_url = "https://pokeapi.co/api/v2/pokemon/"
    pokemon_id = random.randint(1, 898)
    pokemon_data = requests.get(f"{poke_api_url}{pokemon_id}").json()
    pokemon_name = pokemon_data['name'].capitalize()
    pokemon_image_url = pokemon_data['sprites']['front_default']
    print(pokemon_name)
    await ctx.send("Adivina este Pokémon, tienes 30 segundos!")
    #await ctx.send(f"Nombre: {pokemon_name}")
    
    response = requests.get(pokemon_image_url)
    with open("img/pokemon_temp.png", "wb") as file:
        file.write(response.content)

    # Obtener la silueta de la imagen descargada
    imagen_silueta = obtener_silueta("img/pokemon_temp.png")

    # Guardar la imagen de la silueta generada
    imagen_silueta.save("img/silueta_pokemon.png")
    with open("img/silueta_pokemon.png", 'rb') as file:
            picture = discord.File(file)
            await ctx.send(file=picture)
    
   
    
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=30)

        if response.content.lower() == pokemon_name.lower():
            await ctx.send(f"¡Correcto, {ctx.author}! ¡Has adivinado el Pokémon!")
        else:
            await ctx.send(f"¡Incorrecto, {ctx.author}! El Pokémon correcto era {pokemon_name}.")
    except asyncio.TimeoutError:
        await ctx.send(f"Se acabó el tiempo. El Pokémon era {pokemon_name}.")