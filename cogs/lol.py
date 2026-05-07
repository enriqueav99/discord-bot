"""Comandos de League of Legends usando la Riot API (EUW)."""

from __future__ import annotations

import logging

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

_DDRAGON_FALLBACK_VERSION = "14.10.1"


class _RiotRateLimited(Exception):
    """Riot API devolvió 429 — distinguible de 'no encontrado' (None)."""


class LoL(HttpMixin, commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session = None
        self._api_key: str | None = bot.config.riot_api_key
        self._champions: dict[int, str] = {}
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

    async def _resolve(self, invocador: str) -> tuple[dict, dict] | None:
        """Devuelve (summoner_data, account_data) o None si no se encuentra.

        Acepta 'Nombre#TAG' (Riot ID) o nombre de invocador legacy.
        """
        if "#" in invocador:
            game_name, tag_line = invocador.split("#", 1)
            account = await self._riot_get(
                f"{_BASE_REGION}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
            )
            if not account:
                return None
            summoner = await self._riot_get(
                f"{_BASE}/lol/summoner/v4/summoners/by-puuid/{account['puuid']}"
            )
        else:
            summoner = await self._riot_get(
                f"{_BASE}/lol/summoner/v4/summoners/by-name/{invocador}"
            )
            if not summoner:
                return None
            account = {"puuid": summoner["puuid"], "gameName": summoner["name"], "tagLine": "EUW"}

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
            description=f"❌ Invocador `{invocador}` no encontrado en EUW.\nUsa `Nombre#EUW` o el nombre de invocador exacto.",
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
                await self._riot_get(f"{_BASE}/lol/league/v4/entries/by-summoner/{summoner['id']}")
                or []
            )
        except _RiotRateLimited:
            await ctx.send(embed=self._rate_limit_embed())
            return

        version = await self._get_ddragon_version()
        embed = discord.Embed(
            title=f"⚔️ {account.get('gameName', summoner['name'])}",
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
            title=f"⚔️ {account.get('gameName', summoner['name'])} — {resultado}",
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
                f"/by-summoner/{summoner['id']}/top?count=5"
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
            title=f"⚔️ {account.get('gameName', summoner['name'])} — Top maestría",
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


async def setup(bot: commands.Bot):
    await bot.add_cog(LoL(bot))
