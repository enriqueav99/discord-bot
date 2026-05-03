import pytest

from cogs.music import (
    LoopMode,
    Track,
    _extract_video_id,
    _format_duration,
    _info_to_track,
    _needs_resolve,
    _track_embed,
)


def test_format_duration_none():
    assert _format_duration(None) == "?"


def test_format_duration_segundos():
    assert _format_duration(30) == "0:30"


def test_format_duration_minutos():
    assert _format_duration(125) == "2:05"


def test_format_duration_horas():
    assert _format_duration(3725) == "1:02:05"


def test_info_to_track_devuelve_none_sin_url():
    assert _info_to_track({}, "user", 1) is None
    assert _info_to_track({"title": "x"}, "user", 1) is None


def test_info_to_track_basico():
    track = _info_to_track(
        {
            "title": "Canción",
            "url": "http://stream",
            "webpage_url": "https://youtube.com/watch?v=x",
            "thumbnail": "https://i.ytimg.com/x.jpg",
            "duration": 180,
            "uploader": "Canal",
        },
        "alice",
        12345,
    )
    assert track is not None
    assert track.title == "Canción"
    assert track.url == "http://stream"
    assert track.requested_by == "alice"
    assert track.text_channel_id == 12345
    assert track.duration == 180
    assert track.uploader == "Canal"


def test_track_embed_incluye_metadata():
    track = Track(
        title="Test",
        url="http://x",
        requested_by="bob",
        text_channel_id=1,
        duration=60,
        uploader="Canal",
    )
    embed = _track_embed(track, title="▶️", color=0x00FF00)
    assert "Test" in embed.description
    field_names = [f.name for f in embed.fields]
    assert "Canal" in field_names
    assert "Duración" in field_names
    assert "Pidió" in field_names


def test_loop_mode_values():
    assert LoopMode("off") == LoopMode.OFF
    assert LoopMode("track") == LoopMode.TRACK
    assert LoopMode("queue") == LoopMode.QUEUE


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("https://music.youtube.com/watch?v=abc123", True),
        ("https://manifest.googlevideo.com/very-long-stream-url", False),
        ("https://rr1---sn-abc.googlevideo.com/videoplayback?id=x", False),
    ],
)
def test_needs_resolve(url, expected):
    assert _needs_resolve(url) == expected


@pytest.mark.parametrize(
    "url, expected_id",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=abc&list=RDabc", "abc"),
        ("https://not-a-youtube-url.com", None),
        ("", None),
    ],
)
def test_extract_video_id(url, expected_id):
    assert _extract_video_id(url) == expected_id


def test_info_to_track_uses_webpage_url_as_fallback():
    track = _info_to_track(
        {"webpage_url": "https://www.youtube.com/watch?v=abc"},
        "user",
        1,
    )
    assert track is not None
    assert track.url == "https://www.youtube.com/watch?v=abc"
