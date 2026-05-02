"""Healthcheck para Docker: verifica que el heartbeat es reciente."""

from __future__ import annotations

import sys
import time
from pathlib import Path

HEARTBEAT_FILE = Path("/tmp/.bot_alive")
MAX_AGE_SECONDS = 120


def main() -> int:
    if not HEARTBEAT_FILE.exists():
        return 1
    try:
        last = int(HEARTBEAT_FILE.read_text().strip())
    except (ValueError, OSError):
        return 1
    if time.time() - last > MAX_AGE_SECONDS:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
