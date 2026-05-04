import json

import pytest

from src.config import BotConfig


def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_BOT_PREFIX", "!")
    monkeypatch.setenv("DISCORD_ID_CANAL_PRINCIPAL", "111")
    monkeypatch.setenv("DISCORD_ID_CANAL_BOTS", "222")
    cfg = BotConfig.load(variables_path="missing.json")
    assert cfg.token == "tok"
    assert cfg.prefix == "!"
    assert cfg.id_canal_principal == 111
    assert cfg.id_canal_bots == 222


def test_config_falls_back_to_json(tmp_path, monkeypatch):
    f = tmp_path / "vars.json"
    f.write_text(json.dumps({"id_canal_principal": 1, "id_canal_bots": 2}))
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.delenv("DISCORD_ID_CANAL_PRINCIPAL", raising=False)
    monkeypatch.delenv("DISCORD_ID_CANAL_BOTS", raising=False)
    cfg = BotConfig.load(variables_path=str(f))
    assert cfg.id_canal_principal == 1
    assert cfg.id_canal_bots == 2


def test_config_missing_token(monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="DISCORD_BOT_TOKEN"):
        BotConfig.load(variables_path="missing.json")


def test_config_missing_channels(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.delenv("DISCORD_ID_CANAL_PRINCIPAL", raising=False)
    monkeypatch.delenv("DISCORD_ID_CANAL_BOTS", raising=False)
    with pytest.raises(RuntimeError, match="canales"):
        BotConfig.load(variables_path="missing.json")
