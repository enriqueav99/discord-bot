from PIL import Image

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