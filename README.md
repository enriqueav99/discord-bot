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
| 🎮 **Juegos** | Adivina el Pokémon por silueta gen 1–4 (con ranking y recompensa de 25 🪙), trivia |
| 🎂 **Cumpleaños** | Registro por usuario y anuncio automático diario |
| 🔨 **Moderación** | Kick, ban, timeout, clear con logs de auditoría. Warns por usuario (`/warn`, `/infractions`, `/clearwarns`). Automod configurable: palabras prohibidas y límite de menciones. Logging extendido de ediciones, borrados, cambios de nombre/rol, canales e invitaciones. |
| 🛠️ **Utilidad** | Recordatorios (`10m`, `1h30m`, `2d`), polls con reacciones, info de usuario/servidor |
| 🔊 **Voz** | Text-to-speech (Google TTS), rickroll |
| 🎲 **Diversión** | 8ball, dado, moneda, meme, rick |
| 🎰 **Casino y Economía** | Ruleta europea, blackjack (botones interactivos), tragaperras 3×3, doble o nada. Apuestas múltiples con cantidad por apuesta (`negro 50 alto 30`). `/trabajo` cada 8h, atracos grupales (`/heist`), tienda con roles y títulos cosméticos. Fichas persistentes por servidor, recarga cada 6h, ranking con títulos. |
| ⚔️ **League of Legends** | Perfil con rango SoloQ/Flex, última partida, top maestrías, rotación gratis, historial reciente, partida en directo (spectator), retos, equipo de Clash, comparativa de jugadores, estado del servidor EUW e info detallada de campeones. Vía Riot API + Data Dragon. |

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
| `RIOT_API_KEY` | ❌ | Clave de la Riot API (necesaria para los comandos `/lol`). Si está vacía, los comandos avisan al usuario. |

---

## Juegos

| Comando | Descripción |
|---|---|
| `/adivina` | Adivina el Pokémon por la silueta (gen 1–4). Tienes 30s y pista a los 15s. Acertar da **25 🪙** y suma un punto al ranking. |
| `/pokeranking` | Top 10 de aciertos de `/adivina` en el servidor. |
| `/trivia` | Pregunta de trivia de opción múltiple. 20s para responder. |

---

## Casino y Economía

Todos los comandos usan fichas virtuales persistentes por servidor. Cada usuario empieza con **1000 fichas** y puede recargar 500 gratis cada 6h con `/recargar`. También se pueden ganar jugando a `/adivina` (**25 🪙** por acierto).

### Juegos

| Comando | Descripción |
|---|---|
| `/ruleta <apuestas>` | Ruleta europea. Una o varias apuestas con cantidad individual: `negro 50 alto 30 0 20`. Tipos válidos: `rojo negro verde par impar alto bajo 0-36`. |
| `/blackjack [cantidad]` | Blackjack contra la banca con botones Pedir carta / Plantarse. Blackjack natural paga ×2.5. |
| `/tragaperras [cantidad]` | Tragaperras 3×3. La fila central determina el resultado: 3 iguales = jackpot (×3–75 según símbolo), par = empate, resto = pierde. |
| `/doble [cantidad]` | Cara o cruz: doblas o pierdes la apuesta. |

### Economía

| Comando | Descripción |
|---|---|
| `/trabajo` | Trabaja en un oficio aleatorio y gana fichas (50–400 🪙). Cooldown de **8h por servidor**. |
| `/heist <cantidad>` | Inicia un atraco grupal. Los demás tienen **60s** para unirse con `/unirse`. Al finalizar, 50/50 de ganar o perder. |
| `/unirse [cantidad]` | Únete al atraco activo del servidor. |
| `/tienda` | Muestra los artículos disponibles en la tienda del servidor. |
| `/tienda comprar <id>` | Compra un artículo. Los roles se asignan automáticamente y expiran si tienen duración. |
| `/tienda add_rol <rol> <precio> [dias]` | **[Admin]** Añade un rol a la tienda (`0` días = permanente). |
| `/tienda add_titulo <titulo> <precio> [dias]` | **[Admin]** Añade un título cosmético que aparece en `/ranking_fichas`. |
| `/tienda remove <id>` | **[Admin]** Elimina un artículo de la tienda. |

### Fichas

| Comando | Descripción |
|---|---|
| `/fichas` | Consulta tu saldo actual. |
| `/recargar` | Recibe 500 fichas gratis (cooldown 6h por servidor). |
| `/ranking_fichas` | Top 10 del servidor. Los títulos activos se muestran junto al nombre. |

---

## League of Legends

Comandos sobre la región **EUW** vía Riot API. Requieren `RIOT_API_KEY` en el `.env`. Acepta el formato `Nombre#TAG` (Riot ID).

| Comando | Descripción |
|---|---|
| `/lol perfil <inv>` | Rango SoloQ y Flex, nivel y winrate. |
| `/lol partida <inv>` | Última partida: campeón, KDA, CS, modo y duración. |
| `/lol historial <inv> [n]` | Últimas N partidas (1–10, default 5) con KDA y W/L. |
| `/lol enjuego <inv>` | Partida en directo: campeones, hechizos y equipos. |
| `/lol maestria <inv>` | Top 5 campeones por puntos de maestría. |
| `/lol challenges <inv>` | Puntos totales de retos y top 5 mejor percentil. |
| `/lol clash <inv>` | Equipo de Clash si está inscrito. |
| `/lol comparar <inv1> <inv2>` | Comparativa de rango SoloQ/Flex de dos jugadores. |
| `/lol campeon <nombre>` | Pasiva, hechizos Q/W/E/R y stats base de un campeón (Data Dragon). |
| `/lol rotacion` | Campeones gratis de la rotación semanal. |
| `/lol status` | Incidencias y mantenimientos del servidor EUW. |

---

## Moderación

| Comando | Descripción |
|---|---|
| `/kick <miembro> [razón]` | Expulsa a un miembro. |
| `/ban <miembro> [razón]` | Banea a un miembro. |
| `/timeout <miembro> <tiempo> [razón]` | Silencia temporalmente (`10m`, `1h`, `2d`, máx. 28 días). |
| `/clear <cantidad>` | Borra hasta 100 mensajes recientes. |
| `/say <texto>` | El bot repite tu mensaje. |
| `/warn <miembro> [razón]` | Registra un aviso al miembro. |
| `/infractions <miembro>` | Muestra todos los avisos de un miembro. |
| `/clearwarns <miembro>` | Borra todos los avisos de un miembro. |
| `/automod add <palabra>` | Añade una palabra a la lista negra. |
| `/automod remove <palabra>` | Elimina una palabra de la lista negra. |
| `/automod list` | Muestra las palabras prohibidas. |
| `/automod menciones <n>` | Límite máximo de menciones por mensaje (`0` = desactivado). |

---

## Desarrollo

```bash
pip install -r requirements-dev.txt
pytest          # Tests
ruff check .    # Lint
ruff format .   # Formato
```

Para añadir un cog nuevo: crea `cogs/mi_cog.py` con `async def setup(bot): ...` y añádelo a `EXTENSIONS` en `cogs/__init__.py`.
