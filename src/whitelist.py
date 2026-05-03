"""Whitelist de usuarios para comandos restringidos."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_DATA_DIR = Path(os.getenv("BOT_DATA_DIR", str(Path(__file__).parent.parent)))
_WHITELIST_FILE = _DATA_DIR / "whitelist.json"


def _load() -> list[int]:
    if not _WHITELIST_FILE.exists():
        return []
    try:
        return json.loads(_WHITELIST_FILE.read_text(encoding="utf-8")).get("users", [])
    except Exception as e:
        log.error("Error leyendo whitelist: %s", e)
        return []


def _save(users: list[int]) -> None:
    _WHITELIST_FILE.write_text(
        json.dumps({"users": users}, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def is_whitelisted(user_id: int) -> bool:
    return user_id in _load()


def add_user(user_id: int) -> bool:
    """Devuelve True si se añadió, False si ya existía."""
    users = _load()
    if user_id in users:
        return False
    users.append(user_id)
    _save(users)
    return True


def remove_user(user_id: int) -> bool:
    """Devuelve True si se eliminó, False si no existía."""
    users = _load()
    if user_id not in users:
        return False
    users.remove(user_id)
    _save(users)
    return True


def list_users() -> list[int]:
    return _load()
