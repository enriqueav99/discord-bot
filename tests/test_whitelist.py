import src.whitelist as wl_module
from src.whitelist import add_user, is_whitelisted, list_users, remove_user


def test_add_and_check(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_module, "_WHITELIST_FILE", tmp_path / "whitelist.json")
    assert add_user(111) is True
    assert is_whitelisted(111) is True
    assert is_whitelisted(999) is False


def test_add_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_module, "_WHITELIST_FILE", tmp_path / "whitelist.json")
    assert add_user(111) is True
    assert add_user(111) is False  # ya existe


def test_remove(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_module, "_WHITELIST_FILE", tmp_path / "whitelist.json")
    add_user(111)
    assert remove_user(111) is True
    assert is_whitelisted(111) is False


def test_remove_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_module, "_WHITELIST_FILE", tmp_path / "whitelist.json")
    assert remove_user(999) is False


def test_list(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_module, "_WHITELIST_FILE", tmp_path / "whitelist.json")
    add_user(111)
    add_user(222)
    assert list_users() == [111, 222]


def test_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_module, "_WHITELIST_FILE", tmp_path / "whitelist.json")
    assert list_users() == []
    assert is_whitelisted(1) is False
