"""Capa de datos compartida: fichas y tienda."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger("discord.fichas")

_DATA_DIR = Path(os.getenv("BOT_DATA_DIR", "."))
_FICHAS_FILE = _DATA_DIR / "fichas.json"
_SHOP_FILE = _DATA_DIR / "tienda.json"

FICHAS_INICIALES = 1000


def _load_fichas() -> dict:
    if _FICHAS_FILE.exists():
        try:
            return json.loads(_FICHAS_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("No se pudo leer %s, empezando vacío", _FICHAS_FILE)
    return {}


def _save_fichas(data: dict) -> None:
    try:
        _FICHAS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        log.error("No se pudo guardar fichas.json", exc_info=True)


def _load_shop() -> dict:
    if _SHOP_FILE.exists():
        try:
            return json.loads(_SHOP_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("No se pudo leer %s, empezando vacío", _SHOP_FILE)
    return {}


def _save_shop(data: dict) -> None:
    try:
        _SHOP_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        log.error("No se pudo guardar tienda.json", exc_info=True)


class FichasManager:
    def __init__(self) -> None:
        self._fichas: dict = _load_fichas()
        self._shop: dict = _load_shop()
        self.heists: dict[int, dict] = {}

    # ── fichas ────────────────────────────────────────────────────────────────

    def saldo(self, guild_id: int, user_id: int) -> int:
        return self._fichas.get(str(guild_id), {}).get(str(user_id), FICHAS_INICIALES)

    def ajustar(self, guild_id: int, user_id: int, delta: int) -> int:
        gk, uk = str(guild_id), str(user_id)
        actual = self._fichas.setdefault(gk, {}).get(uk, FICHAS_INICIALES)
        nuevo = max(0, actual + delta)
        self._fichas[gk][uk] = nuevo
        _save_fichas(self._fichas)
        return nuevo

    def todos(self, guild_id: int) -> dict[str, int]:
        return self._fichas.get(str(guild_id), {})

    # ── tienda ────────────────────────────────────────────────────────────────

    def guild_shop(self, guild_id: int) -> dict:
        return self._shop.setdefault(str(guild_id), {"items": {}, "next_id": 1, "compras": {}})

    def save_shop(self) -> None:
        _save_shop(self._shop)

    def active_title(self, guild_id: int, user_id: int) -> str | None:
        gs = self._shop.get(str(guild_id), {})
        compras = gs.get("compras", {}).get(str(user_id), {})
        items = gs.get("items", {})
        now = datetime.now(UTC)
        for iid, c in compras.items():
            expira = c.get("expira")
            if expira and datetime.fromisoformat(expira) <= now:
                continue
            item = items.get(iid, {})
            if item.get("tipo") == "titulo":
                return item.get("titulo")
        return None

    def shop_data(self) -> dict:
        return self._shop


_manager: FichasManager | None = None


def get_manager() -> FichasManager:
    global _manager
    if _manager is None:
        _manager = FichasManager()
    return _manager
