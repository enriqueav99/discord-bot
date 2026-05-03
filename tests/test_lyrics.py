import pytest

from cogs.lyrics import _parse_artist_title


@pytest.mark.parametrize(
    "query, expected_artist, expected_title",
    [
        ("Dua Lipa - Levitating", "Dua Lipa", "Levitating"),
        ("The Weeknd - Blinding Lights (Official Video)", "The Weeknd", "Blinding Lights"),
        ("bad guy [Official Music Video]", "", "bad guy"),
        ("Shape of You", "", "Shape of You"),
        ("Artist - Title (feat. Someone) [HD]", "Artist", "Title"),
        ("  Coldplay  -  Yellow  ", "Coldplay", "Yellow"),
    ],
)
def test_parse_artist_title(query, expected_artist, expected_title):
    artist, title = _parse_artist_title(query)
    assert artist == expected_artist
    assert title == expected_title


def test_parse_artist_title_no_separator():
    artist, title = _parse_artist_title("Bohemian Rhapsody")
    assert artist == ""
    assert title == "Bohemian Rhapsody"


def test_parse_artist_title_multiple_dashes():
    # Solo divide en el primero
    artist, title = _parse_artist_title("A - B - C")
    assert artist == "A"
    assert title == "B - C"
