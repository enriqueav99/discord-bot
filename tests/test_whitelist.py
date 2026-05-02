from src.leer_csv import comprobar_whitelist, leer_strings_de_fila


def test_whitelist_existing_user(tmp_path, monkeypatch):
    csv_file = tmp_path / "whitelist.csv"
    csv_file.write_text("alice%bob%charlie")
    monkeypatch.chdir(tmp_path)
    assert comprobar_whitelist("alice") == 1
    assert comprobar_whitelist("bob") == 1
    assert comprobar_whitelist("nadie") == 0


def test_whitelist_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert leer_strings_de_fila() == []
    assert comprobar_whitelist("alguien") == 0
