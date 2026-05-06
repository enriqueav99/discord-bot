# Bot de Discord

[![CI](https://github.com/enriqueav99/discord-bot/actions/workflows/test.yml/badge.svg)](https://github.com/enriqueav99/discord-bot/actions/workflows/test.yml)
[![Lint](https://github.com/enriqueav99/discord-bot/actions/workflows/lint.yml/badge.svg)](https://github.com/enriqueav99/discord-bot/actions/workflows/lint.yml)
[![Docker](https://github.com/enriqueav99/discord-bot/actions/workflows/docker.yml/badge.svg)](https://github.com/enriqueav99/discord-bot/actions/workflows/docker.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

Bot de Discord en Python para servidores pequeños: música de YouTube, mini-juegos, casino, cumpleaños, moderación con logs de auditoría y más.

Usa `/help` en Discord para ver todos los comandos disponibles.

---

## Características

| | |
|---|---|
| 🎵 **Música** | Cola por servidor, autoplay, `playnext`, shuffle, loop, letras en tiempo real, barra de progreso. Se desconecta solo tras 15 min de inactividad. |
| 🎮 **Juegos** | Adivina el Pokémon por silueta gen 1–4 (con ranking), trivia |
| 🎂 **Cumpleaños** | Registro por usuario y anuncio automático diario |
| 🔨 **Moderación** | Kick, ban, timeout y clear con logs de auditoría en canal configurable |
| 🛠️ **Utilidad** | Recordatorios (`10m`, `1h30m`, `2d`), polls con reacciones, info de usuario/servidor |
| 🔊 **Voz** | Text-to-speech (Google TTS), rickroll |
| 🎲 **Diversión** | 8ball, dado, moneda, meme, rick |
| 🎰 **Casino** | Ruleta europea, blackjack (botones interactivos), tragaperras 3×3, doble o nada. Apuestas múltiples con cantidad por apuesta (`negro 50 alto 30`). Fichas persistentes por servidor, recarga cada 6h, ranking. |

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
| `DISCORD_REQUIRED_ROLE` | ❌ | Nombre del rol de Discord necesario para usar el bot (admins siempre pasan) |
| `BOT_DATA_DIR` | ❌ | Directorio donde se guardan `fichas.json` y otros datos persistentes (default `.`) |

---

## Casino

Todos los comandos del casino usan fichas virtuales persistentes por servidor. Cada usuario empieza con **1000 fichas** y puede recargar 500 gratis cada 6h con `/recargar`.

| Comando | Descripción |
|---|---|
| `/ruleta <apuestas>` | Ruleta europea. Una o varias apuestas con cantidad individual: `negro 50 alto 30 0 20`. Tipos válidos: `rojo negro verde par impar alto bajo 0-36`. |
| `/blackjack [cantidad]` | Blackjack contra la banca con botones Pedir carta / Plantarse. Blackjack natural paga ×2.5. |
| `/tragaperras [cantidad]` | Tragaperras 3×3. La fila central determina el resultado: 3 iguales = jackpot (×3–75 según símbolo), par = empate, resto = pierde. |
| `/doble [cantidad]` | Cara o cruz: doblas o pierdes la apuesta. |
| `/fichas` | Consulta tu saldo actual de fichas. |
| `/recargar` | Recibe 500 fichas gratis (cooldown 6h por servidor). |
| `/ranking_fichas` | Top 10 de fichas del servidor. |

---

## Desarrollo

```bash
pip install -r requirements-dev.txt
pytest          # Tests
ruff check .    # Lint
ruff format .   # Formato
```

Para añadir un cog nuevo: crea `cogs/mi_cog.py` con `async def setup(bot): ...` y añádelo a `EXTENSIONS` en `cogs/__init__.py`.
