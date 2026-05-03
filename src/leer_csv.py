"""Whitelist de usuarios permitidos para comandos restringidos."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_WHITELIST_FILE = Path(__file__).parent.parent / "whitelist.csv"


def leer_strings_de_fila() -> list[str]:
    try:
        with _WHITELIST_FILE.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="%")
            first_row = next(reader, None)
            return first_row if first_row is not None else []
    except FileNotFoundError:
        log.warning("Archivo de whitelist no encontrado: %s", _WHITELIST_FILE)
        return []
    except Exception as e:
        log.error("Error leyendo whitelist: %s", e)
        return []


def comprobar_whitelist(usuario: str) -> bool:
    return usuario in leer_strings_de_fila()
