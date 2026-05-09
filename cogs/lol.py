"""Comandos de League of Legends usando la Riot API (EUW)."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata

import discord
from discord import app_commands
from discord.ext import commands

from src.http import HttpMixin

log = logging.getLogger("discord.lol")

_PLATFORM = "euw1"
_REGION = "europe"
_BASE = f"https://{_PLATFORM}.api.riotgames.com"
_BASE_REGION = f"https://{_REGION}.api.riotgames.com"
_DDRAGON = "https://ddragon.leagueoflegends.com"

_TIER_EMOJI = {
    "IRON": "⬛",
    "BRONZE": "🟫",
    "SILVER": "⬜",
    "GOLD": "🟨",
    "PLATINUM": "🟩",
    "EMERALD": "💚",
    "DIAMOND": "💎",
    "MASTER": "🔮",
    "GRANDMASTER": "🔥",
    "CHALLENGER": "👑",
}

_QUEUE_LABEL = {
    "RANKED_SOLO_5x5": "SoloQ",
    "RANKED_FLEX_SR": "Flex",
}

_QUEUE_NAME = {
    420: "SoloQ",
    440: "Flex",
    450: "ARAM",
    400: "Normal Draft",
    430: "Normal Blind",
    700: "Clash",
    900: "URF",
    1020: "One for All",
    1300: "Nexus Blitz",
    1400: "Ultimate Spellbook",
    1700: "Arena",
    1900: "URF",
}

_DDRAGON_FALLBACK_VERSION = "14.10.1"


def _normalize(s: str) -> str:
    """Quita acentos, apóstrofes y mayúsculas para matching de campeones."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c.lower() for c in s if c.isalnum())


def _strip_html(s: str) -> str:
    """Limpia tags HTML/etiquetas de Data Dragon en descripciones."""
    return re.sub(r"<[^>]+>", "", s or "").replace("&nbsp;", " ").strip()


class _RiotRateLimited(Exception):
    """Riot API devolvió 429 — distinguible de 'no encontrado' (None)."""


class LoL(HttpMixin, commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session = None
        self._api_key: str | None = bot.config.riot_api_key
        self._champions: dict[int, str] = {}
        self._summoner_spells: dict[int, str] = {}
        self._challenge_names: dict[int, str] = {}
        self._ddragon_version: str | None = None

    async def _riot_get(self, url: str) -> dict | list | None:
        if not self._api_key:
            return None
        session = await self._get_session()
        try:
            async with session.get(url, headers={"X-Riot-Token": self._api_key}) as r:
                if r.status == 404:
                    return None
                if r.status == 429:
                    log.warning("Riot API rate limit alcanzado")
                    raise _RiotRateLimited
                if r.status != 200:
                    log.warning("Riot API %s → %s", url, r.status)
                    return None
                return await r.json()
        except _RiotRateLimited:
            raise
        except Exception:
            log.exception("Error en petición Riot API: %s", url)
            return None

    async def _ddragon_get(self, url: str) -> dict | list | None:
        session = await self._get_session()
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return None
                return await r.json()
        except Exception:
            log.exception("Error en petición Data Dragon: %s", url)
            return None

    async def _get_ddragon_version(self) -> str:
        if self._ddragon_version:
            return self._ddragon_version
        versions = await self._ddragon_get(f"{_DDRAGON}/api/versions.json")
        self._ddragon_version = versions[0] if versions else _DDRAGON_FALLBACK_VERSION
        return self._ddragon_version

    async def _load_champions(self) -> dict[int, str]:
        if self._champions:
            return self._champions
        version = await self._get_ddragon_version()
        data = await self._ddragon_get(f"{_DDRAGON}/cdn/{version}/data/en_US/champion.json")
        if not data:
            return {}
        self._champions = {int(v["key"]): v["name"] for v in data["data"].values()}
        return self._champions

    async def _load_summoner_spells(self) -> dict[int, str]:
        if self._summoner_spells:
            return self._summoner_spells
        version = await self._get_ddragon_version()
        data = await self._ddragon_get(f"{_DDRAGON}/cdn/{version}/data/en_US/summoner.json")
        if not data:
            return {}
        self._summoner_spells = {int(v["key"]): v["name"] for v in data["data"].values()}
        return self._summoner_spells

    async def _load_challenge_names(self, locale: str = "es_ES") -> dict[int, str]:
        if self._challenge_names:
            return self._challenge_names
        config = await self._riot_get(f"{_BASE}/lol/challenges/v1/challenges/config")
        if not config:
            return {}
        result: dict[int, str] = {}
        for c in config:
            cid = c.get("id")
            names = c.get("localizedNames", {}).get(locale) or {}
            if cid is not None and "name" in names:
                result[int(cid)] = names["name"]
        self._challenge_names = result
        return result

    async def _resolve(self, invocador: str) -> tuple[dict, dict] | None:
        """Devuelve (summoner_data, account_data) o None si no se encuentra.

        Solo acepta 'Nombre#TAG' (Riot ID).
        """
        if "#" not in invocador:
            return None
        game_name, tag_line = invocador.split("#", 1)
        account = await self._riot_get(
            f"{_BASE_REGION}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        )
        if not account:
            return None
        summoner = await self._riot_get(
            f"{_BASE}/lol/summoner/v4/summoners/by-puuid/{account['puuid']}"
        )
        if not summoner:
            return None
        return summoner, account

    # ── /lol ──────────────────────────────────────────────────────────────────

    @commands.hybrid_group(name="lol", description="Comandos de League of Legends ⚔️")
    async def lol(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    def _no_key_embed(self) -> discord.Embed:
        return discord.Embed(
            description="❌ `RIOT_API_KEY` no configurada. Añádela al `.env` del bot.",
            color=discord.Color.red(),
        )

    def _rate_limit_embed(self) -> discord.Embed:
        return discord.Embed(
            description="⏳ La Riot API está limitando las peticiones. Inténtalo de nuevo en unos segundos.",
            color=discord.Color.orange(),
        )

    def _not_found_embed(self, invocador: str) -> discord.Embed:
        return discord.Embed(
            description=f"❌ Invocador `{invocador}` no encontrado en EUW.\nUsa el formato `Nombre#TAG` (p. ej. `Faker#KR1`).",
            color=discord.Color.red(),
        )

    # ── /lol perfil ───────────────────────────────────────────────────────────

    @lol.command(name="perfil", description="Rango y estadísticas de un invocador")
    @app_commands.describe(invocador="Nombre de invocador o Nombre#TAG")
    async def lol_perfil(self, ctx: commands.Context, *, invocador: str):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            result = await self._resolve(invocador)
            if not result:
                await ctx.send(embed=self._not_found_embed(invocador))
                return
            summoner, account = result

            entries = (
                await self._riot_get(f"{_BASE}/lol/league/v4/entries/by-puuid/{summoner['puuid']}")
                or []
            )
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        version = await self._get_ddragon_version()
        embed = discord.Embed(
            title=f"⚔️ {account.get('gameName', invocador)}",
            color=0xC89B3C,
        )
        embed.set_thumbnail(
            url=f"{_DDRAGON}/cdn/{version}/img/profileicon/{summoner['profileIconId']}.png"
        )
        embed.add_field(name="Nivel", value=str(summoner["summonerLevel"]), inline=True)
        embed.add_field(name="Servidor", value="EUW", inline=True)

        ranked = {e["queueType"]: e for e in entries if e["queueType"] in _QUEUE_LABEL}
        if ranked:
            for queue_type, label in _QUEUE_LABEL.items():
                if queue_type not in ranked:
                    continue
                e = ranked[queue_type]
                tier = e["tier"]
                emoji = _TIER_EMOJI.get(tier, "")
                wins, losses = e["wins"], e["losses"]
                total = wins + losses
                wr = round(wins / total * 100) if total else 0
                embed.add_field(
                    name=f"{emoji} {label}",
                    value=f"**{tier} {e['rank']}** — {e['leaguePoints']} LP\n{wins}W {losses}L ({wr}% WR)",
                    inline=False,
                )
        else:
            embed.add_field(name="Ranked", value="Sin partidas clasificatorias", inline=False)

        await ctx.send(embed=embed)

    # ── /lol partida ──────────────────────────────────────────────────────────

    @lol.command(name="partida", description="Última partida de un invocador")
    @app_commands.describe(invocador="Nombre de invocador o Nombre#TAG")
    async def lol_partida(self, ctx: commands.Context, *, invocador: str):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            result = await self._resolve(invocador)
            if not result:
                await ctx.send(embed=self._not_found_embed(invocador))
                return
            summoner, account = result

            match_ids = await self._riot_get(
                f"{_BASE_REGION}/lol/match/v5/matches/by-puuid/{summoner['puuid']}/ids?start=0&count=1"
            )
            if not match_ids:
                await ctx.send(
                    embed=discord.Embed(
                        description="No se encontraron partidas recientes.",
                        color=discord.Color.orange(),
                    )
                )
                return

            match = await self._riot_get(f"{_BASE_REGION}/lol/match/v5/matches/{match_ids[0]}")
            if not match:
                await ctx.send(
                    embed=discord.Embed(
                        description="No se pudo obtener la partida.", color=discord.Color.orange()
                    )
                )
                return
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        # Find the participant
        puuid = summoner["puuid"]
        participant = next((p for p in match["info"]["participants"] if p["puuid"] == puuid), None)
        if not participant:
            await ctx.send(
                embed=discord.Embed(
                    description="No se encontró al jugador en la partida.",
                    color=discord.Color.orange(),
                )
            )
            return

        won = participant["win"]
        champion = participant["championName"]
        kills = participant["kills"]
        deaths = participant["deaths"]
        assists = participant["assists"]
        kda = f"{kills}/{deaths}/{assists}"
        cs = participant["totalMinionsKilled"] + participant.get("neutralMinionsKilled", 0)
        duration_s = match["info"]["gameDuration"]
        duration = f"{duration_s // 60}m {duration_s % 60}s"
        queue_id = match["info"]["queueId"]
        queue_name = {
            420: "SoloQ",
            440: "Flex",
            450: "ARAM",
            400: "Normal Draft",
            430: "Normal Blind",
        }.get(queue_id, f"Modo {queue_id}")

        color = discord.Color.green() if won else discord.Color.red()
        resultado = "Victoria 🏆" if won else "Derrota 💀"

        version = await self._get_ddragon_version()
        embed = discord.Embed(
            title=f"⚔️ {account.get('gameName', invocador)} — {resultado}",
            color=color,
        )
        embed.set_thumbnail(url=f"{_DDRAGON}/cdn/{version}/img/champion/{champion}.png")
        embed.add_field(name="Campeón", value=champion, inline=True)
        embed.add_field(name="Modo", value=queue_name, inline=True)
        embed.add_field(name="Duración", value=duration, inline=True)
        embed.add_field(name="KDA", value=f"**{kda}**", inline=True)
        embed.add_field(name="CS", value=str(cs), inline=True)
        kda_ratio = round((kills + assists) / max(deaths, 1), 2)
        embed.add_field(name="KDA ratio", value=f"{kda_ratio}", inline=True)

        await ctx.send(embed=embed)

    # ── /lol maestria ─────────────────────────────────────────────────────────

    @lol.command(name="maestria", description="Top 5 campeones por maestría")
    @app_commands.describe(invocador="Nombre de invocador o Nombre#TAG")
    async def lol_maestria(self, ctx: commands.Context, *, invocador: str):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            result = await self._resolve(invocador)
            if not result:
                await ctx.send(embed=self._not_found_embed(invocador))
                return
            summoner, account = result

            maestrias = await self._riot_get(
                f"{_BASE}/lol/champion-mastery/v4/champion-masteries"
                f"/by-puuid/{summoner['puuid']}/top?count=5"
            )
            if not maestrias:
                await ctx.send(
                    embed=discord.Embed(
                        description="No hay datos de maestría.", color=discord.Color.orange()
                    )
                )
                return
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        champions = await self._load_champions()
        medallas = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        lines = []
        for i, m in enumerate(maestrias):
            name = champions.get(m["championId"], f"ID {m['championId']}")
            pts = f"{m['championPoints']:,}".replace(",", ".")
            nivel = m["championLevel"]
            lines.append(f"{medallas[i]} **{name}** — Nivel {nivel} · {pts} pts")

        embed = discord.Embed(
            title=f"⚔️ {account.get('gameName', invocador)} — Top maestría",
            description="\n".join(lines),
            color=0xC89B3C,
        )
        await ctx.send(embed=embed)

    # ── /lol rotacion ─────────────────────────────────────────────────────────

    @lol.command(name="rotacion", description="Campeones gratis esta semana")
    async def lol_rotacion(self, ctx: commands.Context):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            data = await self._riot_get(f"{_BASE}/lol/platform/v3/champion-rotations")
            if not data:
                await ctx.send(
                    embed=discord.Embed(
                        description="No se pudo obtener la rotación.", color=discord.Color.orange()
                    )
                )
                return
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        champions = await self._load_champions()
        free_ids: list[int] = data.get("freeChampionIds", [])
        names = sorted(champions.get(cid, f"ID {cid}") for cid in free_ids)

        embed = discord.Embed(
            title="🎁 Campeones gratis esta semana",
            description=", ".join(f"**{n}**" for n in names),
            color=0x0BC4C4,
        )
        embed.set_footer(text="Rotación semanal EUW")
        await ctx.send(embed=embed)

    # ── /lol historial ────────────────────────────────────────────────────────

    @lol.command(name="historial", description="Últimas N partidas (1–10) de un invocador")
    @app_commands.describe(
        invocador="Nombre#TAG",
        cantidad="Cuántas partidas mostrar (1–10, por defecto 5)",
    )
    async def lol_historial(self, ctx: commands.Context, invocador: str, cantidad: int = 5):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        cantidad = max(1, min(cantidad, 10))
        await ctx.defer()
        try:
            result = await self._resolve(invocador)
            if not result:
                await ctx.send(embed=self._not_found_embed(invocador))
                return
            summoner, account = result

            match_ids = await self._riot_get(
                f"{_BASE_REGION}/lol/match/v5/matches/by-puuid/{summoner['puuid']}/ids"
                f"?start=0&count={cantidad}"
            )
            if not match_ids:
                await ctx.send(
                    embed=discord.Embed(
                        description="Sin partidas recientes.",
                        color=discord.Color.orange(),
                    )
                )
                return

            matches = await asyncio.gather(
                *[self._riot_get(f"{_BASE_REGION}/lol/match/v5/matches/{mid}") for mid in match_ids]
            )
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        puuid = summoner["puuid"]
        lines = []
        wins = 0
        for match in matches:
            if not match:
                continue
            p = next(
                (x for x in match["info"]["participants"] if x["puuid"] == puuid),
                None,
            )
            if not p:
                continue
            won = p["win"]
            if won:
                wins += 1
            emoji = "✅" if won else "❌"
            kda = f"{p['kills']}/{p['deaths']}/{p['assists']}"
            cs = p["totalMinionsKilled"] + p.get("neutralMinionsKilled", 0)
            queue = _QUEUE_NAME.get(match["info"]["queueId"], "?")
            dur_min = match["info"]["gameDuration"] // 60
            lines.append(
                f"{emoji} **{p['championName']}** · {kda} · {cs} CS · {queue} · {dur_min}m"
            )

        total = len(lines)
        embed = discord.Embed(
            title=f"⚔️ {account.get('gameName', invocador)} — Últimas {total} partidas",
            description="\n".join(lines) or "Sin datos.",
            color=0xC89B3C,
        )
        if total:
            wr = round(wins / total * 100)
            embed.set_footer(text=f"{wins}W {total - wins}L ({wr}% WR)")
        await ctx.send(embed=embed)

    # ── /lol enjuego ──────────────────────────────────────────────────────────

    @lol.command(name="enjuego", description="Partida en directo (si está jugando)")
    @app_commands.describe(invocador="Nombre#TAG")
    async def lol_enjuego(self, ctx: commands.Context, *, invocador: str):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            result = await self._resolve(invocador)
            if not result:
                await ctx.send(embed=self._not_found_embed(invocador))
                return
            summoner, account = result
            game = await self._riot_get(
                f"{_BASE}/lol/spectator/v5/active-games/by-summoner/{summoner['puuid']}"
            )
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        if not game:
            await ctx.send(
                embed=discord.Embed(
                    description=f"⚪ `{account.get('gameName', invocador)}` no está en partida ahora mismo.",
                    color=discord.Color.light_grey(),
                )
            )
            return

        champions = await self._load_champions()
        spells = await self._load_summoner_spells()
        queue_name = _QUEUE_NAME.get(
            game.get("gameQueueConfigId"), f"Modo {game.get('gameQueueConfigId', '?')}"
        )
        duration_s = max(0, int(game.get("gameLength", 0)))
        duration = f"{duration_s // 60}m {duration_s % 60}s"

        teams: dict[int, list[dict]] = {100: [], 200: []}
        for p in game.get("participants", []):
            teams.setdefault(p.get("teamId", 100), []).append(p)

        def fmt_team(team: list[dict]) -> str:
            out = []
            for p in team:
                champ = champions.get(p.get("championId"), f"ID {p.get('championId')}")
                s1 = spells.get(p.get("spell1Id"), "?")
                s2 = spells.get(p.get("spell2Id"), "?")
                name = p.get("riotId") or p.get("summonerName") or "?"
                out.append(f"**{champ}** ({s1}/{s2}) — {name}")
            return "\n".join(out) or "—"

        embed = discord.Embed(
            title=f"🔴 EN DIRECTO — {account.get('gameName', invocador)}",
            color=discord.Color.red(),
        )
        embed.add_field(name="Modo", value=queue_name, inline=True)
        embed.add_field(name="Duración", value=duration, inline=True)
        embed.add_field(name="🟦 Equipo Azul", value=fmt_team(teams[100]), inline=False)
        embed.add_field(name="🟥 Equipo Rojo", value=fmt_team(teams[200]), inline=False)
        await ctx.send(embed=embed)

    # ── /lol status ───────────────────────────────────────────────────────────

    @lol.command(name="status", description="Estado de los servidores LoL EUW")
    async def lol_status(self, ctx: commands.Context):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            data = await self._riot_get(f"{_BASE}/lol/status/v4/platform-data")
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        if not data:
            await ctx.send(
                embed=discord.Embed(
                    description="No se pudo obtener el estado.",
                    color=discord.Color.orange(),
                )
            )
            return

        incidents = data.get("incidents", [])
        maintenances = data.get("maintenances", [])

        if not incidents and not maintenances:
            await ctx.send(
                embed=discord.Embed(
                    title="🟢 Servidores EUW operativos",
                    description="No hay incidencias ni mantenimientos activos.",
                    color=discord.Color.green(),
                )
            )
            return

        embed = discord.Embed(title="🟡 Estado del servidor EUW", color=discord.Color.orange())

        def _localized(items: list[dict]) -> str | None:
            if not items:
                return None
            es = next((t.get("content") for t in items if t.get("locale") == "es_ES"), None)
            return es or items[0].get("content")

        def add_entries(entries: list[dict], label: str) -> None:
            for e in entries[:3]:
                title = _localized(e.get("titles", [])) or "(sin título)"
                updates = e.get("updates", [])
                body = ""
                if updates:
                    body = _localized(updates[-1].get("translations", [])) or ""
                severity = e.get("incident_severity") or e.get("maintenance_status") or ""
                tag = f" [{severity}]" if severity else ""
                embed.add_field(
                    name=f"{label}: {title}{tag}",
                    value=(body[:300] or "—"),
                    inline=False,
                )

        add_entries(incidents, "🚨 Incidencia")
        add_entries(maintenances, "🛠 Mantenimiento")
        await ctx.send(embed=embed)

    # ── /lol challenges ───────────────────────────────────────────────────────

    @lol.command(name="challenges", description="Retos: puntos totales y top 5 del jugador")
    @app_commands.describe(invocador="Nombre#TAG")
    async def lol_challenges(self, ctx: commands.Context, *, invocador: str):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            result = await self._resolve(invocador)
            if not result:
                await ctx.send(embed=self._not_found_embed(invocador))
                return
            summoner, account = result
            data = await self._riot_get(
                f"{_BASE}/lol/challenges/v1/player-data/{summoner['puuid']}"
            )
            names = await self._load_challenge_names()
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        if not data:
            await ctx.send(
                embed=discord.Embed(description="Sin datos de retos.", color=discord.Color.orange())
            )
            return

        total = data.get("totalPoints", {}) or {}
        challenges = data.get("challenges", []) or []
        sorted_ch = sorted(
            (c for c in challenges if c.get("percentile") is not None),
            key=lambda c: c["percentile"],
        )[:5]

        lines = []
        for c in sorted_ch:
            cid = c.get("challengeId")
            name = names.get(cid, f"Reto {cid}")
            lvl = c.get("level", "?")
            pct = c.get("percentile", 1) * 100
            lines.append(f"• **{name}** — {lvl} (top {pct:.2f}%)")

        embed = discord.Embed(
            title=f"🏆 {account.get('gameName', invocador)} — Retos",
            color=0xC89B3C,
        )
        current = total.get("current", 0) or 0
        max_pts = total.get("max", 0) or 0
        embed.add_field(
            name="Puntos totales",
            value=f"**{current:,}** / {max_pts:,} ({total.get('level', '?')})",
            inline=False,
        )
        if lines:
            embed.add_field(
                name="Top 5 retos (mejor percentil)",
                value="\n".join(lines),
                inline=False,
            )
        await ctx.send(embed=embed)

    # ── /lol clash ────────────────────────────────────────────────────────────

    @lol.command(name="clash", description="Equipo de Clash del invocador (si está inscrito)")
    @app_commands.describe(invocador="Nombre#TAG")
    async def lol_clash(self, ctx: commands.Context, *, invocador: str):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            result = await self._resolve(invocador)
            if not result:
                await ctx.send(embed=self._not_found_embed(invocador))
                return
            summoner, account = result
            registrations = await self._riot_get(
                f"{_BASE}/lol/clash/v1/players/by-puuid/{summoner['puuid']}"
            )
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        if not registrations:
            await ctx.send(
                embed=discord.Embed(
                    description=f"⚪ `{account.get('gameName', invocador)}` no está inscrito en Clash.",
                    color=discord.Color.light_grey(),
                )
            )
            return

        reg = next((r for r in registrations if r.get("teamId")), None)
        if not reg:
            await ctx.send(
                embed=discord.Embed(
                    description="Inscrito en Clash pero sin equipo asignado.",
                    color=discord.Color.orange(),
                )
            )
            return

        try:
            team = await self._riot_get(f"{_BASE}/lol/clash/v1/teams/{reg['teamId']}")
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        if not team:
            await ctx.send(
                embed=discord.Embed(
                    description="No se pudo obtener el equipo.",
                    color=discord.Color.orange(),
                )
            )
            return

        members = team.get("players", []) or []
        member_lines = [f"• `{m.get('position', '?')}` ({m.get('role', '?')})" for m in members]
        embed = discord.Embed(
            title=f"⚔️ {team.get('name', '(sin nombre)')} — Clash",
            description=f"`[{team.get('abbreviation', '???')}]` · Tier {team.get('tier', '?')}",
            color=0xC89B3C,
        )
        embed.add_field(
            name=f"Miembros ({len(members)})",
            value="\n".join(member_lines) or "—",
            inline=False,
        )
        await ctx.send(embed=embed)

    # ── /lol comparar ─────────────────────────────────────────────────────────

    @lol.command(name="comparar", description="Compara el rango SoloQ/Flex de dos jugadores")
    @app_commands.describe(
        inv1="Primer invocador (Nombre#TAG)",
        inv2="Segundo invocador (Nombre#TAG)",
    )
    async def lol_comparar(self, ctx: commands.Context, inv1: str, inv2: str):
        if not self._api_key:
            await ctx.send(embed=self._no_key_embed(), ephemeral=True)
            return

        await ctx.defer()
        try:
            r1, r2 = await asyncio.gather(self._resolve(inv1), self._resolve(inv2))
            if not r1:
                await ctx.send(embed=self._not_found_embed(inv1))
                return
            if not r2:
                await ctx.send(embed=self._not_found_embed(inv2))
                return
            s1, a1 = r1
            s2, a2 = r2
            e1, e2 = await asyncio.gather(
                self._riot_get(f"{_BASE}/lol/league/v4/entries/by-puuid/{s1['puuid']}"),
                self._riot_get(f"{_BASE}/lol/league/v4/entries/by-puuid/{s2['puuid']}"),
            )
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        def summary(entries: list[dict] | None, queue_type: str) -> str:
            for e in entries or []:
                if e.get("queueType") == queue_type:
                    tier = e["tier"]
                    emoji = _TIER_EMOJI.get(tier, "")
                    wins, losses = e["wins"], e["losses"]
                    total = wins + losses
                    wr = round(wins / total * 100) if total else 0
                    return f"{emoji} **{tier} {e['rank']}** · {e['leaguePoints']} LP · {wr}% WR"
            return "—"

        n1 = a1.get("gameName", inv1)
        n2 = a2.get("gameName", inv2)
        embed = discord.Embed(title="⚔️ Comparativa", color=0xC89B3C)
        embed.add_field(
            name=f"🟦 {n1}",
            value=(
                f"SoloQ: {summary(e1, 'RANKED_SOLO_5x5')}\nFlex: {summary(e1, 'RANKED_FLEX_SR')}"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"🟥 {n2}",
            value=(
                f"SoloQ: {summary(e2, 'RANKED_SOLO_5x5')}\nFlex: {summary(e2, 'RANKED_FLEX_SR')}"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

    # ── /lol campeon ──────────────────────────────────────────────────────────

    @lol.command(name="campeon", description="Información de un campeón (pasiva, hechizos, stats)")
    @app_commands.describe(nombre="Nombre del campeón (p. ej. Yasuo, Kha'Zix)")
    async def lol_campeon(self, ctx: commands.Context, *, nombre: str):
        await ctx.defer()
        version = await self._get_ddragon_version()
        listing = await self._ddragon_get(f"{_DDRAGON}/cdn/{version}/data/en_US/champion.json")
        if not listing:
            await ctx.send(
                embed=discord.Embed(
                    description="No se pudo cargar la lista de campeones.",
                    color=discord.Color.orange(),
                )
            )
            return

        target = _normalize(nombre)
        match_id: str | None = None
        for cid, c in listing["data"].items():
            if _normalize(c["name"]) == target or _normalize(cid) == target:
                match_id = cid
                break
        if not match_id:
            for cid, c in listing["data"].items():
                if target and target in _normalize(c["name"]):
                    match_id = cid
                    break
        if not match_id:
            await ctx.send(
                embed=discord.Embed(
                    description=f"❌ Campeón `{nombre}` no encontrado.",
                    color=discord.Color.red(),
                )
            )
            return

        detail = await self._ddragon_get(
            f"{_DDRAGON}/cdn/{version}/data/en_US/champion/{match_id}.json"
        )
        if not detail:
            await ctx.send(
                embed=discord.Embed(
                    description="No se pudo obtener el detalle del campeón.",
                    color=discord.Color.orange(),
                )
            )
            return

        c = detail["data"][match_id]
        spells = c.get("spells", [])
        passive = c.get("passive", {})
        stats = c.get("stats", {})

        embed = discord.Embed(
            title=f"⚔️ {c['name']} — *{c['title']}*",
            description=_strip_html(c.get("blurb", ""))[:500],
            color=0xC89B3C,
        )
        embed.set_thumbnail(url=f"{_DDRAGON}/cdn/{version}/img/champion/{match_id}.png")
        embed.add_field(
            name=f"🌀 Pasiva: {passive.get('name', '?')}",
            value=_strip_html(passive.get("description", ""))[:300] or "—",
            inline=False,
        )
        spell_keys = ["Q", "W", "E", "R"]
        for i, s in enumerate(spells[:4]):
            embed.add_field(
                name=f"{spell_keys[i]}: {s.get('name', '?')}",
                value=_strip_html(s.get("description", ""))[:250] or "—",
                inline=False,
            )
        embed.add_field(
            name="Stats base",
            value=(
                f"HP: {stats.get('hp', '?')} · "
                f"AD: {stats.get('attackdamage', '?')} · "
                f"Armor: {stats.get('armor', '?')} · "
                f"MR: {stats.get('spellblock', '?')}"
            ),
            inline=False,
        )
        tags = c.get("tags", [])
        if tags:
            embed.set_footer(text=" / ".join(tags))
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LoL(bot))
