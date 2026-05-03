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
| General | `ping`, `saludar`, `info`, `help` |
| Diversión | `8ball`, `dado`, `moneda`, `choose`, `meme`, `rick` |
| Juegos | `adivina` (Pokémon), `trivia` |
| Voz | `join`, `leave`, `rr`, `tts` |
| Música | `play`, `playnext`, `queue`, `skip`, `pause`, `resume`, `stop`, `clearqueue`, `remove`, `shuffle`, `loop`, `nowplaying`, `volume`, `autoplay` |
| Letras | `lyrics` |
| Cumpleaños | `cumple set`, `cumple del`, `cumple lista` |
| Utilidad | `userinfo`, `serverinfo`, `avatar`, `poll`, `recordatorio` |
| Moderación | `clear`, `kick`, `ban`, `timeout`, `say` |

## Funcionalidades destacadas

- **Cola de música por servidor** con auto-disconnect tras 2 minutos sin gente
- **Autoplay**: al vaciarse la cola encola automáticamente canciones relacionadas vía YouTube Mix
- **`playnext`**: inserta una canción como la siguiente (sin esperar al final de la cola)
- **Letras** (`lyrics`) con búsqueda por título o canción actual, paginado automático
- **Cumpleaños** (`cumple set/del/lista`): registro persistente + anuncio automático diario
- **TTS** (`tts`): convierte texto a voz y lo reproduce en el canal de voz (Google TTS)
- **Logs de moderación**: kick, ban, timeout y clear se registran en `DISCORD_ID_CANAL_LOGS` si está configurado
- **`help`** dinámico: genera la lista de comandos con descripciones y parámetros desde el código
- **Recordatorios** (`recordatorio`) con formato `10m`, `1h30m`, `2d` — avisa por DM
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
