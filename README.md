# Bot de Korea

Bot de Discord en Python con cogs, slash commands, cola de música, mini-juegos,
moderación y utilidades varias.

## Inicio rápido

### 1. Configurar variables

Copia `.env.example` a `.env` y rellena:

```bash
cp .env.example .env
```

Variables:

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DISCORD_BOT_TOKEN` | ✅ | Token del bot |
| `DISCORD_BOT_PREFIX` | ❌ | Prefijo (default `<`) |
| `DISCORD_ID_CANAL_PRINCIPAL` | ✅* | Canal de bienvenidas |
| `DISCORD_ID_CANAL_BOTS` | ✅* | Canal de salida del bot |
| `DISCORD_BOT_CAM` | ❌ | Dispositivo v4l2 para `/aloe` |

\* También se aceptan vía `variables.json` legacy.

### 2. Lanzar con Docker Compose

```bash
docker compose up -d --build
```

### 3. O en local

```bash
pip install -r requirements-dev.txt
python main.py
```

## Comandos

Todos los comandos funcionan tanto con prefijo (`<ping`) como con slash (`/ping`).

| Categoría | Comandos |
|---|---|
| General | `ping`, `saludar`, `info`, `help_korea` |
| Diversión | `8ball`, `dado`, `moneda`, `choose`, `meme`, `rick` |
| Juegos | `adivina` (Pokémon), `trivia` |
| Voz | `join`, `leave`, `rr`, `aloe` |
| Música | `play`, `queue`, `skip`, `pause`, `resume`, `stop`, `nowplaying`, `volume` |
| Utilidad | `userinfo`, `serverinfo`, `avatar`, `poll`, `recordatorio` |
| Moderación | `clear`, `kick`, `ban`, `timeout`, `say` |

## Funcionalidades destacadas

- **Cola de música por servidor** con auto-disconnect tras 2 minutos sin gente
- **Slash commands** sincronizados al inicio
- **Healthcheck en Docker** vía `healthcheck.py`
- **Logs rotativos** + salida a stdout (visible en `docker logs`)
- **Dotenv** para configuración local
- **Whitelist por nombre** (`whitelist.csv`, separado por `%`)
- **Tests** con pytest + lint con ruff
- **CI**: ruff, pytest (3.11/3.12), build docker, CodeQL, Dependabot

## Desarrollo

```bash
# Tests
pytest

# Lint
ruff check .
ruff format .
```

Para añadir un cog nuevo: crea `cogs/mi_cog.py` con `async def setup(bot): ...`
y añádelo a `EXTENSIONS` en `cogs/__init__.py`.

## Otros

### Go

Hay una rama `go-bot` con una prueba en Go. Lo bueno de Go es que podríamos crear
un ejecutable y que cualquier persona pudiera correr el bot sin tener Go
instalado ni saber programar.
