"""Carga y validación de configuración del bot."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class BotConfig:
    token: str
    prefix: str
    id_canal_principal: int
    id_canal_bots: int
    id_canal_logs: int | None
    dj_role_name: str

    @classmethod
    def load(cls, variables_path: str = "variables.json") -> BotConfig:
        token = os.getenv("DISCORD_BOT_TOKEN")
        prefix = os.getenv("DISCORD_BOT_PREFIX", "<")
        id_canal_principal = os.getenv("DISCORD_ID_CANAL_PRINCIPAL")
        id_canal_bots = os.getenv("DISCORD_ID_CANAL_BOTS")

        if not token or not id_canal_principal or not id_canal_bots:
            path = Path(variables_path)
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                token = token or data.get("token")
                id_canal_principal = id_canal_principal or data.get("id_canal_principal")
                id_canal_bots = id_canal_bots or data.get("id_canal_bots")

        if not token:
            raise RuntimeError(
                "DISCORD_BOT_TOKEN no está definido en el entorno ni en variables.json"
            )

        if not id_canal_principal or not id_canal_bots:
            raise RuntimeError(
                "Faltan IDs de canales. Define DISCORD_ID_CANAL_PRINCIPAL y "
                "DISCORD_ID_CANAL_BOTS o crea variables.json"
            )

        raw_logs = os.getenv("DISCORD_ID_CANAL_LOGS")
        dj_role_name = os.getenv("DISCORD_DJ_ROLE")

        if not dj_role_name:
            raise RuntimeError("DISCORD_DJ_ROLE no está definido en el entorno")
        return cls(
            token=token,
            prefix=prefix,
            id_canal_principal=int(id_canal_principal),
            id_canal_bots=int(id_canal_bots),
            id_canal_logs=int(raw_logs) if raw_logs else None,
            dj_role_name=dj_role_name,
        )
