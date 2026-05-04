# Bot de Korea

[![CI](https://github.com/enriqueav99/discord-bot/actions/workflows/test.yml/badge.svg)](https://github.com/enriqueav99/discord-bot/actions/workflows/test.yml)
[![Lint](https://github.com/enriqueav99/discord-bot/actions/workflows/lint.yml/badge.svg)](https://github.com/enriqueav99/discord-bot/actions/workflows/lint.yml)
[![Docker](https://github.com/enriqueav99/discord-bot/actions/workflows/docker.yml/badge.svg)](https://github.com/enriqueav99/discord-bot/actions/workflows/docker.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

Bot de Discord en Python para servidores pequeños: música de YouTube, mini-juegos, cumpleaños, moderación con logs de auditoría y más.

Usa `/help` en Discord para ver todos los comandos, o `/docs` para una guía rápida.

---

## Características

| | |
|---|---|
| 🎵 **Música** | Cola por servidor, autoplay, `playnext`, shuffle, loop, letras en tiempo real, barra de progreso. Se desconecta solo tras 15 min de inactividad. |
| 🎮 **Juegos** | Adivina el Pokémon por silueta (con ranking), trivia *(adivina requiere whitelist)* |
| 🎂 **Cumpleaños** | Registro por usuario y anuncio automático diario |
| 🔨 **Moderación** | Kick, ban, timeout y clear con logs de auditoría en canal configurable |
| 🛠️ **Utilidad** | Recordatorios (`10m`, `1h30m`, `2d`), polls con reacciones, info de usuario/servidor |
| 🔊 **Voz** | Text-to-speech (Google TTS), rickroll *(requieren whitelist)* |
| 🎲 **Diversión** | 8ball, dado, moneda, meme, rick |
| 📋 **Whitelist** | Lista de usuarios con acceso a comandos restringidos; gestionada con `/whitelist` (solo admins) |

---

## Inicio rápido

```bash
cp .env.example .env        # Rellena DISCORD_BOT_TOKEN y los IDs de canales
docker compose up -d --build
```

Ver `.env.example` para todas las variables disponibles.

### Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DISCORD_BOT_TOKEN` | ✅ | Token del bot |
| `DISCORD_BOT_PREFIX` | ❌ | Prefijo (default `<`) |
| `DISCORD_ID_CANAL_PRINCIPAL` | ✅ | Canal de bienvenidas y cumpleaños |
| `DISCORD_ID_CANAL_BOTS` | ✅ | Canal de salida del bot |
| `DISCORD_ID_CANAL_LOGS` | ❌ | Canal de logs de moderación y eventos del bot |
| `DISCORD_DJ_ROLE` | ✅ | Rol requerido para usar todos los comandos salvo moderación |

---

## Whitelist

Algunos comandos (`rr`, `tts`, `adivina`) requieren que el usuario esté en la whitelist. Se gestiona desde Discord con comandos de admin:

```
/whitelist add @usuario     — añade a la whitelist
/whitelist remove @usuario  — elimina de la whitelist
/whitelist list             — muestra la whitelist actual
```

La whitelist se guarda en `whitelist.json` en el directorio del bot.

---

## Desarrollo

```bash
pip install -r requirements-dev.txt
pytest          # Tests
ruff check .    # Lint
ruff format .   # Formato
```

Para añadir un cog nuevo: crea `cogs/mi_cog.py` con `async def setup(bot): ...` y añádelo a `EXTENSIONS` en `cogs/__init__.py`.
