import time

import healthcheck


def test_healthcheck_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(healthcheck, "HEARTBEAT_FILE", tmp_path / "missing")
    assert healthcheck.main() == 1


def test_healthcheck_recent(monkeypatch, tmp_path):
    f = tmp_path / "alive"
    f.write_text(str(int(time.time())))
    monkeypatch.setattr(healthcheck, "HEARTBEAT_FILE", f)
    assert healthcheck.main() == 0


def test_healthcheck_stale(monkeypatch, tmp_path):
    f = tmp_path / "alive"
    f.write_text(str(int(time.time()) - 10_000))
    monkeypatch.setattr(healthcheck, "HEARTBEAT_FILE", f)
    assert healthcheck.main() == 1


def test_healthcheck_garbage(monkeypatch, tmp_path):
    f = tmp_path / "alive"
    f.write_text("not a number")
    monkeypatch.setattr(healthcheck, "HEARTBEAT_FILE", f)
    assert healthcheck.main() == 1
