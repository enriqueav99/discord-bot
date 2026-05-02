FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Patch discord.py: treat 4006 (stale session) as a permanent disconnect, not retriable.
# Without this, poll_voice_ws retries indefinitely on 4006 instead of disconnecting cleanly.
RUN python -c "\
import discord, re; \
p = discord.__file__.replace('__init__.py', 'voice_client.py'); \
code = open(p).read(); \
code = code.replace('if exc.code in (1000, 4015):', 'if exc.code in (1000, 4006, 4015):'); \
open(p, 'w').write(code)"

COPY . .

RUN useradd --create-home --shell /bin/bash bot \
    && chown -R bot:bot /app
USER bot

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python healthcheck.py

CMD ["python", "-u", "main.py"]
