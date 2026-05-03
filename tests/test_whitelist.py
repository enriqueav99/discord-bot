import src.leer_csv as leer_csv
from src.leer_csv import comprobar_whitelist, leer_strings_de_fila


def test_whitelist_existing_user(tmp_path, monkeypatch):
    csv_file = tmp_path / "whitelist.csv"
    csv_file.write_text("alice%bob%charlie")
    monkeypatch.setattr(leer_csv, "_WHITELIST_FILE", csv_file)
    assert comprobar_whitelist("alice") is True
    assert comprobar_whitelist("bob") is True
    assert comprobar_whitelist("nadie") is False


def test_whitelist_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(leer_csv, "_WHITELIST_FILE", tmp_path / "whitelist.csv")
    assert leer_strings_de_fila() == []
    assert comprobar_whitelist("alguien") is False
