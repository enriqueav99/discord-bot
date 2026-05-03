from datetime import date
from unittest.mock import patch

import pytest

import cogs.birthdays as bd_module
from cogs.birthdays import _load, _next_occurrence, _save


@pytest.fixture()
def tmp_birthday_file(tmp_path):
    f = tmp_path / "birthdays.json"
    with patch.object(bd_module, "BIRTHDAY_FILE", f):
        yield f


def test_load_returns_empty_if_missing(tmp_birthday_file):
    assert _load() == {}


def test_save_and_load_roundtrip(tmp_birthday_file):
    data = {"123": {"456": "12-25"}}
    with patch.object(bd_module, "BIRTHDAY_FILE", tmp_birthday_file):
        _save(data)
        assert _load() == data


def test_load_handles_corrupt_file(tmp_birthday_file):
    tmp_birthday_file.write_text("NOT JSON", encoding="utf-8")
    with patch.object(bd_module, "BIRTHDAY_FILE", tmp_birthday_file):
        assert _load() == {}


@pytest.mark.parametrize(
    "mmdd, today, expected_days",
    [
        ("12-25", date(2026, 12, 25), 0),
        ("12-25", date(2026, 12, 24), 1),
        ("01-01", date(2026, 12, 31), 1),  # año nuevo
        ("06-15", date(2026, 6, 14), 1),
    ],
)
def test_days_until_birthday(mmdd, today, expected_days):
    month, day = int(mmdd[:2]), int(mmdd[3:])
    bd = _next_occurrence(month, day, today)
    assert (bd - today).days == expected_days


@pytest.mark.parametrize(
    "month, day, today, expected_year",
    [
        (2, 29, date(2025, 3, 1), 2028),  # año no bisiesto, ya pasó → 2028
        (2, 29, date(2028, 2, 29), 2028),  # hoy mismo en año bisiesto → 2028
        (2, 29, date(2028, 3, 1), 2032),  # año bisiesto pero ya pasó → 2032
        (2, 29, date(2025, 1, 1), 2028),  # año no bisiesto, aún no ha pasado → 2028
    ],
)
def test_next_occurrence_leap_day(month, day, today, expected_year):
    bd = _next_occurrence(month, day, today)
    assert bd == date(expected_year, 2, 29)
