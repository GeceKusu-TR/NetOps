def test_native_qt_shell_exposes_netops_pages_without_fluent_widgets():
    from netops_qt_shell import (
        native_legacy_layout_contract,
        native_animation_contract,
        native_brand_contract,
        native_motion_contract,
        native_now_playing_contract,
        native_page_keys,
        native_settings_sections,
        native_sidebar_contract,
        native_sidebar_icon_contract,
        native_visual_contract,
        native_window_contract,
    )

    assert native_page_keys() == (
        "chat",
        "devices",
        "now_playing",
        "automations",
        "remote",
        "system",
        "notifications",
        "settings",
    )
    contract = native_legacy_layout_contract()
    assert contract["top_status"] == ("SİSTEM", "REMOTE", "BİLDİRİMLER", "NOW PLAYING")
    assert contract["sidebar"] == (
        "Genel Bakış",
        "Cihazlar",
        "Now Playing",
        "Otomasyonlar",
        "Remote",
        "Ayarlar",
    )
    assert contract["bottom_input"] == "Mesajını yaz..."
    motion = native_motion_contract()
    assert motion == {"startup_ms": 220, "page_ms": 180, "property": "windowOpacity"}
    assert native_animation_contract() == {
        "logo_fade_ms": 260,
        "sidebar_stagger_ms": 35,
        "button_feedback_ms": 120,
    }
    assert native_brand_contract() == {
        "app_name": "NetOps",
        "version": "1.52",
        "window_title": "NetOps 1.52",
        "logo_file": "Logo.png",
    }
    assert native_visual_contract() == {
        "now_playing_poll_ms": 1500,
        "system_poll_ms": 1000,
        "button_radius_px": 10,
        "button_feedback_ms": 120,
    }
    assert native_window_contract() == {"start_maximized": True}
    assert native_settings_sections() == (
        "Genel",
        "Sistem",
        "Görünüm",
        "Pencere Yöneticisi",
        "Netolab",
        "Güvenlik",
        "Güncellemeler",
        "Hakkında",
    )
    assert native_sidebar_contract() == {
        "settings_button_count": 1,
        "panel_radius_px": 16,
        "status_message": "",
        "settings_position": "bottom",
    }
    assert native_sidebar_icon_contract() == {
        "chat": "message",
        "devices": "computer",
        "now_playing": "media",
        "automations": "workflow",
        "system": "system",
        "settings": "settings",
    }
    assert native_now_playing_contract() == {
        "fullscreen_title": "ŞU AN ÇALIYOR",
        "standby_title": "BEKLEME MODU",
        "refresh_ms": 1500,
    }


def test_native_qt_backend_keeps_command_execution_explicit():
    from netops_qt_backend import build_qt_backend

    backend = build_qt_backend()

    result = backend.run("command", "deneme")

    assert result["ok"] is False
    assert "bağlı" in result["error"]


def test_native_qt_backend_normalizes_chat_callback():
    from netops_qt_backend import build_qt_backend

    backend = build_qt_backend(chat_reader=lambda text: f"NetOps: {text}")

    assert backend.run("chat", "merhaba") == "NetOps: merhaba"


def test_native_qt_backend_exposes_remote_and_notifications_callbacks():
    from netops_qt_backend import build_qt_backend

    backend = build_qt_backend(
        remote_reader=lambda text: {"ok": True, "display_text": f"uzak: {text}"},
        notifications_reader=lambda: [{"title": "Test", "detail": "Bildirim hazır"}],
    )

    assert backend.run("remote", "telefon durumu") == {"ok": True, "display_text": "uzak: telefon durumu"}
    assert backend.run("notifications") == [{"title": "Test", "detail": "Bildirim hazır"}]


def test_native_qt_backend_uses_existing_netops_chat_engine(monkeypatch):
    import sys
    from types import SimpleNamespace

    from netops_qt_backend import build_qt_backend

    monkeypatch.setitem(
        sys.modules,
        "neto_ai",
        SimpleNamespace(neto_ai_cevap_ver=lambda text: f"cevap: {text}"),
    )

    assert build_qt_backend().run("chat", "test") == "cevap: test"


def test_native_qt_backend_can_speak_chat_replies_without_blocking_chat():
    from netops_qt_backend import build_qt_backend

    spoken = []
    backend = build_qt_backend(
        chat_reader=lambda text: f"cevap: {text}",
        speech_runner=lambda text: spoken.append(text) or {"ok": True},
    )

    assert backend.run("chat", "merhaba") == "cevap: merhaba"
    assert backend.run("speech", "cevap: merhaba") == {"ok": True}
    assert spoken == ["cevap: merhaba"]


def test_native_qt_window_builds_all_pages_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow, native_page_keys

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow(
        build_qt_backend(system_reader=lambda: {"cpu": 1, "ram": 2, "devices": 0, "remote": "Hazır"})
    )

    assert tuple(window._pages) == native_page_keys()
    assert window.windowTitle() == "NetOps 1.52"
    window.close()
    app.processEvents()


def test_native_theme_palette_uses_saved_legacy_theme_and_accent():
    from netops_qt_shell import native_theme_palette

    palette = native_theme_palette({"tema": "light", "renk_temasi": "blue"})

    assert palette["bg"] == "#F4F5F7"
    assert palette["sidebar"] == "#FFFFFF"
    assert palette["accent"] == "#3B82F6"
    assert palette["accent_hover"] == "#326DCF"


def test_native_settings_exposes_saved_color_theme_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow(
        build_qt_backend(settings_reader=lambda: {"tema": "light", "renk_temasi": "green"})
    )

    assert "renk_temasi" in window._settings_controls
    assert window._native_palette["accent"] == "#22C55E"
    assert "#F4F5F7" in window.styleSheet()
    assert "QCheckBox::indicator:checked" in window.styleSheet()
    assert "QAbstractItemView::item:selected" in window.styleSheet()
    window.close()
    app.processEvents()


def test_native_settings_tabs_use_fluent_sizing_and_navigation_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow()
    tabs = window._settings_tabs

    assert tabs is not None
    assert tabs.documentMode() is True
    assert tabs.usesScrollButtons() is False
    assert tabs.tabBar().expanding() is False
    assert tabs.tabBar().minimumHeight() >= 40
    window.close()
    app.processEvents()


def test_native_qt_window_has_live_now_playing_timer_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow(
        build_qt_backend(media_reader=lambda: {"title": "Test Parça", "artist": "Test Sanatçı"})
    )

    assert window._now_playing_timer.interval() == 1500
    window._refresh_now_playing()
    assert not hasattr(window, "_sidebar_now_playing")
    assert "Test Parça" in window._top_status_buttons["NOW PLAYING"].text()
    window.close()
    app.processEvents()


def test_native_qt_now_playing_uses_right_button_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow(
        build_qt_backend(media_reader=lambda: {"title": "Uzun parça adı", "artist": "Sanatçı"})
    )

    status_layout = window.centralWidget().layout().itemAt(0).layout()
    now_playing_button = window._top_status_buttons["NOW PLAYING"]

    assert status_layout.itemAt(status_layout.count() - 1).widget() is now_playing_button
    assert status_layout.indexOf(window._now_playing_island) == -1
    now_playing_button.click()
    assert window._page_stack.currentWidget() is window._pages["now_playing"]
    window.close()
    app.processEvents()


def test_native_qt_top_status_buttons_start_at_left_without_logo_offscreen():
    from PySide6.QtWidgets import QApplication, QPushButton

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow(build_qt_backend())
    status_layout = window.centralWidget().layout().itemAt(0).layout()

    assert status_layout is not None
    assert isinstance(status_layout.itemAt(0).widget(), QPushButton)
    assert status_layout.itemAt(0).widget() is window._top_status_buttons["SİSTEM"]
    assert window._top_logo is None
    window.close()
    app.processEvents()


def test_native_qt_window_refreshes_separate_ram_and_gpu_every_second_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow(
        build_qt_backend(system_reader=lambda: {"cpu": 4, "ram": 61, "gpu": 27, "devices": 0, "remote": "Hazır"})
    )

    assert window._system_timer.interval() == 1000
    assert set(window._system_values) >= {"ram", "gpu"}
    assert not hasattr(window, "_sidebar_now_playing")
    window._refresh_system()
    assert window._system_values["ram"][0].text() == "61"
    assert window._system_values["gpu"][0].text() == "27"
    window.close()
    app.processEvents()


def test_native_qt_backend_reads_gpu_utilization_from_nvidia_smi(monkeypatch):
    import subprocess

    from netops_qt_backend import _read_gpu_usage

    class Completed:
        stdout = "42\n"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Completed())

    assert _read_gpu_usage() == "42%"


def test_native_qt_window_builds_settings_page_and_button_feedback_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_shell import NetOpsQtWindow, native_page_keys

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow()

    assert "settings" in native_page_keys()
    assert "remote" in native_page_keys()
    assert "notifications" in native_page_keys()
    assert window._pages["settings"] is not None
    assert window._settings_tabs.count() == 8
    assert window._button_feedback_animations == {}
    assert window._buttons_with_feedback
    window.close()
    app.processEvents()


def test_native_qt_chat_composer_is_modern_and_functional_offscreen():
    from PySide6.QtWidgets import QApplication, QFrame

    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow()

    assert isinstance(window._chat_composer, QFrame)
    assert window._chat_composer.objectName() == "chatComposer"
    assert window._chat_input.objectName() == "chatComposerInput"
    assert window._chat_send_button.objectName() == "chatSendButton"
    assert window._chat_mode_button is None
    assert window._chat_input.placeholderText() == "Mesajını yaz..."
    window.close()
    app.processEvents()


def test_native_qt_button_click_starts_feedback_animation_offscreen(monkeypatch):
    from PySide6.QtWidgets import QApplication

    from netops_qt_shell import NetOpsQtWindow

    monkeypatch.delenv("NETOPS_REDUCE_MOTION", raising=False)
    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow()
    button = window._nav_buttons["devices"]

    button.click()
    app.processEvents()

    assert id(button) in window._button_feedback_animations
    window.close()
    app.processEvents()


def test_native_qt_now_playing_page_has_media_controls_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    actions = []
    window = NetOpsQtWindow(
        build_qt_backend(
            media_reader=lambda: {"title": "Test Parça", "artist": "Test Sanatçı"},
            media_control_runner=lambda action: actions.append(action) or {"ok": True},
        )
    )

    window._media_action("next")
    assert actions == ["next"]
    assert window._now_playing_values["title"].text() == "Test Parça"
    window.close()
    app.processEvents()


def test_native_qt_now_playing_page_has_volume_controls_offscreen():
    from PySide6.QtWidgets import QApplication

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow

    app = QApplication.instance() or QApplication([])
    actions = []
    window = NetOpsQtWindow(
        build_qt_backend(
            media_reader=lambda: {"title": "Test Parça"},
            media_control_runner=lambda action: actions.append(action) or {"ok": True, "value": 42, "muted": False},
        )
    )

    window._open_native_page("now_playing")
    assert window._volume_slider.value() == 42
    window._volume_slider.setValue(42)
    window._set_volume()
    window._toggle_mute()

    assert actions == ["volume_get", "volume_set:42", "mute_toggle"]
    window.close()
    app.processEvents()


def test_native_qt_fullscreen_now_playing_has_platform_volume_and_playback_controls(monkeypatch):
    from PySide6.QtWidgets import QApplication

    from netops_qt_backend import build_qt_backend
    from netops_qt_shell import NetOpsQtWindow

    monkeypatch.delenv("NETOPS_REDUCE_MOTION", raising=False)
    app = QApplication.instance() or QApplication([])
    actions = []
    window = NetOpsQtWindow(
        build_qt_backend(
            media_reader=lambda: {
                "title": "Test Parça",
                "artist": "Test Sanatçı",
                "album": "Test Albüm",
                "app": "YouTube Music",
                "playback_status": "Playing",
                "position_seconds": 45,
                "duration_seconds": 180,
            },
            media_control_runner=lambda action: actions.append(action) or {"ok": True, "value": 64, "muted": False},
        )
    )

    window._open_now_playing_fullscreen()
    assert window._now_playing_overlay_platform.text() == "Platform: YouTube Music"
    assert window._now_playing_overlay_play_pause.text() == "Durdur"
    assert window._now_playing_overlay_volume_slider.value() == 64
    assert window._now_playing_overlay_album.text() == "Albüm: Test Albüm"
    assert window._now_playing_overlay_timeline.text() == "00:45 / 03:00"
    assert window._now_playing_overlay_progress.value() == 250
    assert window._now_playing_overlay_visualizer.text()

    window._now_playing_overlay_volume_slider.setValue(72)
    window._set_fullscreen_volume()
    window._fullscreen_media_action("previous")
    window._fullscreen_media_action("play_pause")
    window._fullscreen_media_action("next")
    window._fullscreen_media_action("mute_toggle")
    assert actions[-5:] == ["volume_set:72", "previous", "play_pause", "next", "mute_toggle"]
    window._close_now_playing_fullscreen()
    window.close()
    app.processEvents()
