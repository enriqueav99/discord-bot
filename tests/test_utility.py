from datetime import timedelta

from cogs.utility import parse_duration


def test_parse_simple_minutes():
    assert parse_duration("10m") == timedelta(minutes=10)


def test_parse_combined():
    assert parse_duration("1h30m") == timedelta(hours=1, minutes=30)


def test_parse_days():
    assert parse_duration("2d") == timedelta(days=2)


def test_parse_seconds_minutes_hours_days():
    assert parse_duration("1d2h3m4s") == timedelta(days=1, hours=2, minutes=3, seconds=4)


def test_parse_invalid_returns_none():
    assert parse_duration("hola") is None


def test_parse_zero_returns_none():
    assert parse_duration("0m") is None


def test_parse_uppercase():
    assert parse_duration("5M") == timedelta(minutes=5)
