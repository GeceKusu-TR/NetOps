from __future__ import annotations

import neto_now_playing as now_playing


def test_media_session_key_is_stable_and_normalized():
    assert now_playing._session_key("Spotify!App", "  Song  ", "Artist") == "spotify!app|song|artist"


def test_invalid_media_action_is_rejected_without_os_input():
    assert now_playing.media_session_control("run_command") is False


def test_session_selection_is_local_preference():
    old = now_playing.selected_media_session()
    try:
        assert now_playing.select_media_session("spotify|song|artist") is True
        assert now_playing.selected_media_session() == "spotify|song|artist"
        assert now_playing.select_media_session("") is False
        assert now_playing.selected_media_session() == ""
    finally:
        now_playing.select_media_session(old)
