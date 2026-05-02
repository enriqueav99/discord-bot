from cogs.music import LoopMode, Track, _format_duration, _info_to_track, _track_embed


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
