# Usamos la imagen base oficial de Python
FROM python:3.9-slim

# Instalamos ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Establecemos el directorio de trabajo en el contenedor
WORKDIR /app

# Copiamos los archivos de tu aplicación al contenedor
COPY . .

# Instalamos las dependencias del bot (si tienes un requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar el bot cuando se inicie el contenedor
CMD ["python", "main.py"]
